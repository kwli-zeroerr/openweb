<script lang="ts">
    import { onMount, onDestroy, createEventDispatcher, tick } from 'svelte';
    import * as pdfjsLib from 'pdfjs-dist';
  
    /**
     * A production-ready PDF canvas viewer for Svelte using pdfjs-dist.
     * Features:
     * - Lazy per-page rendering via IntersectionObserver
     * - High-DPI rendering (devicePixelRatio aware)
     * - Smooth scroll + accurate current page tracking
     * - Optional text selection layer (no pdfjs viewer UI required)
     * - Resize-aware (recalculates scale on container resize)
     * - External controls: next/prev/goToPage/changeScale
     * - Clean teardown & render task cancellation
     */
  
    // ======= Props =======
    export let fileUrl: string;                 // Absolute or relative URL to the PDF
    export let initialScale: number = 1.0;      // Base logical scale (1.0 = 100%)
    export let fit: 'width' | 'none' = 'width'; // Auto-fit to container width when 'width'
    export let minScale = 0.25;
    export let maxScale = 4.0;
    export let pageGap = 12;                    // px gap between pages
    export let showToolbar = true;
    export let enableTextSelection = true;
    export let authToken: string | null = null;  // Optional authentication token
  
    const dispatch = createEventDispatcher();
  
    // ======= pdf.js worker configuration =======
    // Make sure this path is accessible from your static assets.
    // You can also use a CDN path if desired.
    // Example of local: /pdfjs/pdf.worker.min.mjs
    // Example of CDN: https://cdn.jsdelivr.net/npm/pdfjs-dist@4.8.69/build/pdf.worker.min.mjs
    (pdfjsLib as any).GlobalWorkerOptions.workerSrc = '/pdfjs/pdf.worker.min.mjs';
  
    // ======= State =======
    let container: HTMLDivElement;            // scroll container
    let pagesHost: HTMLDivElement;            // element that holds page containers
    let pdfDoc: any = null;
    let totalPages = 0;
    let currentPage = 1;                      // 1-based
    let loading = true;
    let error: string | null = null;
  
    // Effective scale depends on fit mode & container width
    let baseScale = initialScale;
    let effectiveScale = initialScale;
  
    // Maps & sets for elements and statuses
    type PageEntry = {
      num: number;
      div: HTMLDivElement;       // page container (position:relative)
      canvas: HTMLCanvasElement;  // the raster layer
      textLayer?: HTMLDivElement; // optional text selection layer
      renderedScale?: number;     // scale used for the last render
      renderTask?: any;           // pdf.js renderTask for cancellation
      textRendered?: boolean;     // flag to avoid re-building text layer
      viewportWidth?: number;     // logical width for 1.0 scale
    };
  
    const pageMap = new Map<number, PageEntry>();
  
    // IntersectionObserver for lazy rendering & visibility ratio tracking
    let io: IntersectionObserver | null = null;
  
    // Resize observer for container width changes
    let ro: ResizeObserver | null = null;
  
    // ======= Utilities =======
    function clamp(n: number, min: number, max: number) {
      return Math.max(min, Math.min(max, n));
    }
  
    function px(n: number) { return `${n}px`; }
  
    function cancelRender(entry: PageEntry) {
      try { entry.renderTask?.cancel(); } catch {}
      entry.renderTask = undefined;
    }
  
    function computeEffectiveScale(pageViewportWidthAt1x: number) {
      if (!container) return baseScale;
      if (fit === 'width') {
        // 获取容器的实际可用宽度（减去滚动条和padding）
        const padding = 32; // 增加一些padding以确保页面不会太紧贴边缘
        const scrollbarWidth = 17; // 滚动条宽度（大约）
        const target = container.clientWidth - padding - scrollbarWidth;
        if (pageViewportWidthAt1x && target > 0) {
          const fitScale = target / pageViewportWidthAt1x;
          // 只使用 fitScale，不使用 baseScale 乘数，确保完全适应宽度
          return clamp(fitScale, minScale, maxScale);
        }
      }
      return clamp(baseScale, minScale, maxScale);
    }
  
    function deviceScale() {
      return Math.max(1, window.devicePixelRatio || 1);
    }
  
    function setCurrentPage(n: number) {
      const clamped = clamp(Math.round(n), 1, totalPages);
      if (clamped !== currentPage) {
        currentPage = clamped;
        dispatch('pagechange', { currentPage, totalPages });
      }
    }
  
    // Determine the most visible page in viewport
    function updateVisiblePage() {
      if (!container) return;
      let bestPage = currentPage;
      let bestRatio = 0;
      const viewport = container.getBoundingClientRect();
      pageMap.forEach((entry, num) => {
        const rect = entry.div.getBoundingClientRect();
        const visibleWidth = Math.max(0, Math.min(rect.right, viewport.right) - Math.max(rect.left, viewport.left));
        const visibleHeight = Math.max(0, Math.min(rect.bottom, viewport.bottom) - Math.max(rect.top, viewport.top));
        const visibleArea = visibleWidth * visibleHeight;
        const totalArea = rect.width * rect.height || 1;
        const ratio = visibleArea / totalArea;
        if (ratio > bestRatio) { bestRatio = ratio; bestPage = num; }
      });
      setCurrentPage(bestPage);
    }
  
    // ======= Rendering =======
    async function ensureRendered(pageNum: number) {
      const entry = pageMap.get(pageNum);
      if (!entry || !pdfDoc) return;
  
      // Avoid duplicate renders for same scale
      if (entry.renderedScale && Math.abs(entry.renderedScale - effectiveScale) < 1e-3) return;
  
      cancelRender(entry);
  
      const page = await pdfDoc.getPage(pageNum);
      const viewport = page.getViewport({ scale: 1.0 });
  
      // Cache logical width for fit calculations
      entry.viewportWidth = viewport.width;
  
      // Compute scale
      effectiveScale = computeEffectiveScale(viewport.width);
  
      const v = page.getViewport({ scale: effectiveScale });
      const dpr = deviceScale();
  
      // Prepare canvas with HiDPI backing store
      const { canvas } = entry;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
  
      const outputScale = dpr;
      canvas.style.width = px(v.width);
      canvas.style.height = px(v.height);
      canvas.width = Math.floor(v.width * outputScale);
      canvas.height = Math.floor(v.height * outputScale);
  
      const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : undefined;
  
      // Clear for re-render
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
  
      // Render
      const renderTask = page.render({ canvasContext: ctx, viewport: v, transform });
      entry.renderTask = renderTask;
  
      await renderTask.promise.catch(() => {/* canceled */});
  
      entry.renderedScale = effectiveScale;
  
      if (enableTextSelection && !entry.textRendered) {
        // Basic text layer: map text items into absolutely-positioned spans
        const textContent = await page.getTextContent();
        buildTextLayer(entry, v, textContent);
        entry.textRendered = true;
      }
  
      dispatch('pagerender', { pageNum, width: v.width, height: v.height, scale: effectiveScale });
    }
  
    function buildTextLayer(entry: PageEntry, viewport: any, textContent: any) {
      // Remove previous text layer if exists
      entry.textLayer?.remove();
  
      const textLayerDiv = document.createElement('div');
      textLayerDiv.className = 'textLayer';
      textLayerDiv.style.position = 'absolute';
      textLayerDiv.style.left = '0';
      textLayerDiv.style.top = '0';
      textLayerDiv.style.width = px(viewport.width);
      textLayerDiv.style.height = px(viewport.height);
      textLayerDiv.style.pointerEvents = 'none'; // let selection happen but ignore clicks
  
      // Build individual text spans
      const { items } = textContent;
      for (const item of items) {
        const span = document.createElement('span');
        const tx = pdfjsLib.Util.transform(viewport.transform, item.transform);
        const x = tx[4];
        const y = tx[5];
        const fontSize = Math.hypot(tx[0], tx[2]);
        span.textContent = item.str;
        span.style.position = 'absolute';
        span.style.transformOrigin = '0 0';
        span.style.transform = `translate(${x}px, ${y - fontSize}px)`; // adjust baseline
        span.style.fontSize = `${fontSize}px`;
        span.style.fontFamily = 'sans-serif';
        span.style.whiteSpace = 'pre';
        // Keep opacity low to keep selection but not visible overlay
        span.style.opacity = '0.01';
        textLayerDiv.appendChild(span);
      }
  
      entry.div.appendChild(textLayerDiv);
      entry.textLayer = textLayerDiv;
    }
  
    function createPageEntry(num: number): PageEntry {
      const div = document.createElement('div');
      div.className = 'pdf-page';
      div.style.position = 'relative';
      div.style.margin = `${pageGap / 2}px auto`;
      div.style.padding = '0';
      div.style.background = 'white';
      div.style.boxShadow = '0 1px 2px rgba(0,0,0,0.06)';
      div.style.border = '1px solid var(--pdf-border, #e5e7eb)';
  
      const canvas = document.createElement('canvas');
      canvas.className = 'pdf-canvas';
      canvas.style.display = 'block';
  
      div.appendChild(canvas);
  
      const entry: PageEntry = { num, div, canvas };
      pageMap.set(num, entry);
      if (pagesHost) {
        pagesHost.appendChild(div);
      } else {
        console.error('pagesHost not available when creating page entry');
      }
      return entry;
    }
  
    async function buildPages() {
      // 等待DOM更新，确保pagesHost已经绑定
      await tick();
      
      // 如果还是没有绑定，重试几次
      let retries = 0;
      const maxRetries = 10;
      while (!pagesHost && retries < maxRetries) {
        await tick();
        await new Promise(resolve => setTimeout(resolve, 10));
        retries++;
      }
      
      if (!pagesHost) {
        console.error('pagesHost still not bound after retries');
        return;
      }
      
      pagesHost.innerHTML = '';
      pageMap.clear();
      for (let i = 1; i <= totalPages; i += 1) {
        createPageEntry(i);
      }
    }
  
    function observePages() {
      io?.disconnect();
      io = new IntersectionObserver(async (entries) => {
        // Render visible pages & update current page via highest intersection ratio
        let best: { num: number; ratio: number } | null = null;
        for (const e of entries) {
          const num = Number((e.target as HTMLElement).dataset.pagenum || '0');
          if (e.isIntersecting) {
            await ensureRendered(num);
          }
          if (!best || e.intersectionRatio > best.ratio) {
            best = { num, ratio: e.intersectionRatio };
          }
        }
        if (best) setCurrentPage(best.num);
      }, { root: container, rootMargin: '200px 0px', threshold: [0, 0.01, 0.25, 0.5, 0.75, 1] });
  
      pageMap.forEach((entry) => {
        entry.div.dataset.pagenum = String(entry.num);
        io!.observe(entry.div);
      });
    }
  
    function teardown() {
      io?.disconnect(); io = null;
      ro?.disconnect(); ro = null;
      pageMap.forEach((entry) => cancelRender(entry));
      pageMap.clear();
      try { pdfDoc?.destroy(); } catch {}
      pdfDoc = null;
    }
  
    async function openPdf() {
      loading = true; error = null;
      try {
        // Prepare custom headers for authentication
        const httpHeaders: Record<string, string> = {};
        if (authToken) {
          httpHeaders['Authorization'] = `Bearer ${authToken}`;
        }
        
        // Use range requests and streaming when possible
        const loadingTask = pdfjsLib.getDocument({
          url: fileUrl,
          withCredentials: true,
          useWorkerFetch: true,
          rangeChunkSize: 65536,
          cMapUrl: `https://cdn.jsdelivr.net/npm/pdfjs-dist@${(pdfjsLib as any).version}/cmaps/`,
          cMapPacked: true,
          httpHeaders: Object.keys(httpHeaders).length > 0 ? httpHeaders : undefined,
        });
  
        pdfDoc = await loadingTask.promise;
        totalPages = pdfDoc.numPages;
        currentPage = 1;
        dispatch('loaded', { totalPages });

        // 先设置 loading = false，让 pagesHost 元素渲染出来
        loading = false;
        // 等待 DOM 更新，确保 pagesHost 已经绑定
        await tick();
        await new Promise(resolve => setTimeout(resolve, 10));

        await buildPages();
        observePages();

        // Prime first page
        await ensureRendered(1);
  
        // After first render, recompute effectiveScale for fit mode
        // 确保所有页面都使用正确的缩放比例
        const first = pageMap.get(1);
        if (first?.viewportWidth) {
          const newScale = computeEffectiveScale(first.viewportWidth);
          if (Math.abs(newScale - effectiveScale) > 0.01) {
            effectiveScale = newScale;
            // 重新渲染第一页以应用新的缩放
            await ensureRendered(1);
          }
        }
  
      } catch (e: any) {
        error = e?.message || 'Failed to load PDF';
        loading = false;
      }
    }
  
    function onScroll() {
      updateVisiblePage();
    }
  
    function onResize() {
      // Recompute effective scale and re-render visible pages
      // Keep baseScale the same; just recalc effective for fit mode
      const first = pageMap.get(1);
      if (first?.viewportWidth) {
        const newScale = computeEffectiveScale(first.viewportWidth);
        if (Math.abs(newScale - effectiveScale) > 0.01) {
          effectiveScale = newScale;
        }
      }
      
      pageMap.forEach((entry) => {
        entry.renderedScale = undefined; // force re-render on demand
        // also remove text layer to rebuild with new scale
        if (entry.textLayer) { entry.textLayer.remove(); entry.textLayer = undefined; entry.textRendered = false; }
      });
      // Trigger re-render of the most visible page immediately
      ensureRendered(currentPage);
    }
  
    // ======= Controls (exported) =======
    export async function goToPage(pageNum: number) {
      const target = clamp(pageNum, 1, totalPages);
      const entry = pageMap.get(target);
      if (!entry) return;
      entry.div.scrollIntoView({ behavior: 'smooth', block: 'start' });
      await ensureRendered(target);
      setCurrentPage(target);
    }
  
    export function nextPage() { goToPage(currentPage + 1); }
    export function prevPage() { goToPage(currentPage - 1); }
  
    export async function changeScale(newBaseScale: number) {
      baseScale = clamp(newBaseScale, minScale, maxScale);
      // invalidate all pages to force re-render at new scale
      pageMap.forEach((entry) => {
        entry.renderedScale = undefined;
        cancelRender(entry);
        // Remove text layer to rebuild with new scale
        if (entry.textLayer) { entry.textLayer.remove(); entry.textLayer = undefined; entry.textRendered = false; }
      });
      await ensureRendered(currentPage);
      dispatch('scalechange', { scale: baseScale });
    }
  
    // ======= Lifecycle =======
    let keyHandler: ((e: KeyboardEvent) => void) | null = null;

    onMount(async () => {
      // 等待DOM完全准备好，确保container和pagesHost都已绑定
      await tick();
      await new Promise(resolve => setTimeout(resolve, 0));
      
      // 再次确认DOM元素已绑定
      if (!container || !pagesHost) {
        await tick();
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      
      await openPdf();

      // 再次检查 container 是否存在（防止组件在异步操作期间被卸载）
      if (!container || !pagesHost) {
        console.warn('PDFViewer: container or pagesHost is null, skipping event listeners');
        return;
      }

      // Hook scroll and resize
      container.addEventListener('scroll', onScroll, { passive: true });

      ro = new ResizeObserver(() => onResize());
      ro.observe(container);

      // Keyboard shortcuts on container focus
      keyHandler = (e: KeyboardEvent) => {
        if (e.key === 'ArrowRight' || e.key === 'PageDown') { e.preventDefault(); nextPage(); }
        if (e.key === 'ArrowLeft' || e.key === 'PageUp')   { e.preventDefault(); prevPage(); }
        if (e.key === '+') { e.preventDefault(); changeScale(baseScale + 0.1); }
        if (e.key === '-') { e.preventDefault(); changeScale(baseScale - 0.1); }
        if (e.key === 'Home') { e.preventDefault(); goToPage(1); }
        if (e.key === 'End')  { e.preventDefault(); goToPage(totalPages); }
      };
      container.addEventListener('keydown', keyHandler);
    });

    onDestroy(() => {
      if (container && keyHandler) {
        container.removeEventListener('scroll', onScroll as any);
        container.removeEventListener('keydown', keyHandler as any);
      }
      teardown();
    });
  </script>
  
  {#if showToolbar}
    <div class="toolbar">
      <div class="left">
        <button class="btn" on:click={prevPage} disabled={currentPage<=1} title="上一页">←</button>
        <div class="page-input">
          <input type="number" min="1" max={totalPages} bind:value={currentPage} on:change={() => goToPage(currentPage)} />
          <span class="total">/ {totalPages || 0}</span>
        </div>
        <button class="btn" on:click={nextPage} disabled={currentPage>=totalPages} title="下一页">→</button>
      </div>
      <div class="right">
        <button class="btn" on:click={() => changeScale(baseScale - 0.1)} title="缩小">-</button>
        <span class="scale">{Math.round(baseScale*100)}%</span>
        <button class="btn" on:click={() => changeScale(baseScale + 0.1)} title="放大">+</button>
      </div>
    </div>
  {/if}
  
  <div class="viewer" bind:this={container} tabindex="0" aria-label="PDF viewer">
    {#if loading}
      <div class="center">加载 PDF 中…</div>
    {:else if error}
      <div class="center error">PDF 加载失败：{error}</div>
    {:else}
      <div class="pages" bind:this={pagesHost}></div>
    {/if}
  </div>
  
  <style>
    :global(:root){
      --pdf-border: #e5e7eb;
      --pdf-bg: #f8fafc;
      --pdf-toolbar: #f3f4f6;
      --pdf-text: #111827;
      --pdf-muted: #6b7280;
    }
    .toolbar{
      display:flex;justify-content:space-between;align-items:center;
      padding:8px 12px;background:var(--pdf-toolbar);border-bottom:1px solid var(--pdf-border);
      gap:12px;position:sticky;top:0;z-index:5;
    }
    .toolbar .left,.toolbar .right{display:flex;align-items:center;gap:8px}
    .btn{padding:6px 10px;border:1px solid var(--pdf-border);background:#fff;border-radius:8px;cursor:pointer}
    .btn:disabled{opacity:.5;cursor:not-allowed}
    .page-input{display:flex;align-items:center;gap:6px}
    .page-input input{width:64px;text-align:center;padding:6px;border:1px solid var(--pdf-border);border-radius:6px}
    .total{color:var(--pdf-muted)}
    .scale{min-width:48px;text-align:center;color:var(--pdf-muted)}
  
    .viewer{height:100%;width:100%;overflow:auto;outline:none;background:var(--pdf-bg)}
    .center{display:flex;align-items:center;justify-content:center;height:60vh;color:var(--pdf-muted)}
    .error{color:#dc2626}
  
    .pages{display:flex;flex-direction:column;align-items:center;padding:16px}
    .pdf-page{background:white}
    .pdf-canvas{display:block;width:100%;height:auto}
  
    /* Optional, improve text selection feel (invisible spans) */
    .textLayer span::selection{background: rgba(180,213,255,.65)}
  </style>
  