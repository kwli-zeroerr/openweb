import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig(({ mode }) => ({
	plugins: [
		sveltekit(),
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',
					dest: 'wasm'
				},
				{
					src: 'node_modules/pdfjs-dist/build/pdf.worker.min.mjs',
					dest: 'pdfjs'
				}
			]
		})
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || '1.2.0')
	},
	build: {
		// production defaults
		sourcemap: mode === 'development',
		minify: 'esbuild', // 使用 esbuild 获得更快的构建速度
		outDir: 'dist',
		assetsInlineLimit: 4096,
		rollupOptions: {
			output: {
				// 手动分块以获得更好的压缩
				manualChunks: (id) => {
					if (id.includes('node_modules')) {
						// 将大型库单独打包
						if (id.includes('@tiptap')) {
							return 'tiptap';
						}
						if (id.includes('codemirror')) {
							return 'codemirror';
						}
						if (id.includes('chart.js')) {
							return 'chart';
						}
						// 其他 node_modules
						return 'vendor';
					}
				},
				// 压缩输出文件名
				chunkFileNames: 'js/[name]-[hash].js',
				entryFileNames: 'js/[name]-[hash].js',
				assetFileNames: 'assets/[name]-[hash].[ext]'
			}
		}
	},
	worker: {
		format: 'es'
	},
	ssr: {
		external: ['bits-ui', '@melt-ui/svelte']
	},
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug', 'console.error']
	}
	,
	server: {
		port: 5174,
		strictPort: true,
		allowedHosts: ['test111.zeroerr.team', 'gptapi.zeroerr.team', 'don1.annon.cc', 'don3.annon.cc'],
		host: true,
		watch: {
			ignored: ['**/backend/**', '**/node_modules/**']
		},
		proxy: (() => {
			// Use env-configured target(s); avoid hardcoding any URLs/IPs
			const TARGET = process.env.VITE_PROXY_TARGET || process.env.API_TARGET;
			let proxy: Record<string, import('vite').ProxyOptions> | undefined = undefined;
			if (TARGET) {
				const common = { changeOrigin: true, secure: false } as const;
				proxy = {
					'/api': { target: TARGET, ...common },
					'/ollama': { target: TARGET, ...common },
					'/openai': { target: TARGET, ...common },
					'/ws': { target: TARGET, ws: true, ...common }
				};
			}
			return proxy;
		})()
	},
	preview: {
		port: 5174,
		host: true
	}
}));
