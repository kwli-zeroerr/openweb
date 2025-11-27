import { marked } from 'marked';
import markedKatexExtension from '$lib/utils/marked/katex-extension';
import markedExtension from '$lib/utils/marked/extension';
import { mentionExtension } from '$lib/utils/marked/mention-extension';

// 自定义渲染器，为每个元素添加 data-sourcepos
class SourcePosRenderer extends marked.Renderer {
  private lineOffsets: number[] = [];
  private originalText: string = '';

  constructor(text: string) {
    super();
    this.originalText = text;
    this.lineOffsets = this.computeLineOffsets(text);
  }

  private computeLineOffsets(text: string): number[] {
    const arr = [0];
    for (let i = 0; i < text.length; i++) {
      if (text[i] === '\n') arr.push(i + 1);
    }
    return arr;
  }

  private getSourcePos(token: any): string {
    if (!token.raw) return '';
    
    // 找到 token.raw 在原文中的位置
    const rawStart = this.originalText.indexOf(token.raw);
    if (rawStart === -1) return '';
    
    const rawEnd = rawStart + token.raw.length;
    
    // 转换为行列格式
    const startLine = this.lineOffsets.findIndex(offset => offset > rawStart) - 1;
    const endLine = this.lineOffsets.findIndex(offset => offset > rawEnd) - 1;
    
    const startCol = rawStart - (this.lineOffsets[startLine] || 0) + 1;
    const endCol = rawEnd - (this.lineOffsets[endLine] || 0) + 1;
    
    return `${startLine + 1}:${startCol}-${endLine + 1}:${endCol}`;
  }

  // 重写各种元素的渲染方法
  heading(text: string, level: number, raw: string) {
    const sourcePos = this.getSourcePos({ raw });
    return `<h${level} data-sourcepos="${sourcePos}">${text}</h${level}>`;
  }

  paragraph(text: string) {
    // 对于段落，我们需要特殊处理，因为 marked 不会直接提供 raw
    return `<p data-sourcepos="">${text}</p>`;
  }

  code(code: string, language: string | undefined, isEscaped: boolean) {
    const sourcePos = this.getSourcePos({ raw: code });
    return `<code data-sourcepos="${sourcePos}">${code}</code>`;
  }

  codespan(code: string) {
    const sourcePos = this.getSourcePos({ raw: code });
    return `<code data-sourcepos="${sourcePos}">${code}</code>`;
  }

  blockquote(quote: string) {
    return `<blockquote data-sourcepos="">${quote}</blockquote>`;
  }

  list(body: string, ordered: boolean, start: number) {
    const tag = ordered ? 'ol' : 'ul';
    return `<${tag} data-sourcepos="">${body}</${tag}>`;
  }

  listitem(text: string, task: boolean, checked: boolean) {
    return `<li data-sourcepos="">${text}</li>`;
  }

  table(header: string, body: string) {
    return `<table data-sourcepos=""><thead>${header}</thead><tbody>${body}</tbody></table>`;
  }

  tablerow(content: string) {
    return `<tr data-sourcepos="">${content}</tr>`;
  }

  tablecell(content: string, flags: any) {
    const tag = flags.header ? 'th' : 'td';
    return `<${tag} data-sourcepos="">${content}</${tag}>`;
  }

  // 处理数学公式 - 使用与聊天模板相同的方式
  blockKatex(text: string) {
    console.log('渲染块级KaTeX:', text);
    const sourcePos = this.getSourcePos({ raw: text });
    // 返回原始文本，让 markedKatexExtension 处理渲染
    return `${text}`;
  }

  inlineKatex(text: string) {
    console.log('渲染行内KaTeX:', text);
    const sourcePos = this.getSourcePos({ raw: text });
    // 返回原始文本，让 markedKatexExtension 处理渲染
    return `${text}`;
  }
}

// 渲染为 HTML（包含 data-sourcepos）
export async function renderWithSourcePos(md: string): Promise<string> {
  console.log('开始渲染 Markdown，内容长度:', md.length);
  
  const renderer = new SourcePosRenderer(md);
  
  const options = {
    renderer: renderer,
    throwOnError: false,
    breaks: true,
    gfm: true,
    pedantic: false,
    sanitize: false,
    smartLists: true,
    smartypants: false
  };

  // 使用与聊天模板完全相同的扩展
  marked.use(markedKatexExtension(options));
  marked.use(markedExtension(options));
  marked.use({
    extensions: [mentionExtension({ triggerChar: '@' }), mentionExtension({ triggerChar: '#' })]
  });

  const html = marked(md, options);
  console.log('渲染完成，HTML长度:', html.length);
  console.log('包含KaTeX相关标签:', html.includes('katex'));
  console.log('包含data-sourcepos:', html.includes('data-sourcepos'));
  
  return html;
}
