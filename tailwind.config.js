import typography from '@tailwindcss/typography';
import containerQueries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				gray: {
					50: 'var(--color-gray-50, #f9f9f9)',
					100: 'var(--color-gray-100, #ececec)',
					200: 'var(--color-gray-200, #e3e3e3)',
					300: 'var(--color-gray-300, #cdcdcd)',
					400: 'var(--color-gray-400, #b4b4b4)',
					500: 'var(--color-gray-500, #9b9b9b)',
					600: 'var(--color-gray-600, #676767)',
					700: 'var(--color-gray-700, #4e4e4e)',
					800: 'var(--color-gray-800, #333)',
					850: 'var(--color-gray-850, #262626)',
					900: 'var(--color-gray-900, #171717)',
					950: 'var(--color-gray-950, #0d0d0d)'
				}
			},
			typography: {
				DEFAULT: {
					css: {
						pre: false,
						code: false,
						'pre code': false,
						'code::before': false,
						'code::after': false,
						'--tw-prose-body': '#374151',
						'--tw-prose-headings': '#111827',
						'--tw-prose-lead': '#4b5563',
						'--tw-prose-links': '#111827',
						'--tw-prose-bold': '#111827',
						'--tw-prose-counters': '#6b7280',
						'--tw-prose-bullets': '#d1d5db',
						'--tw-prose-hr': '#e5e7eb',
						'--tw-prose-quotes': '#111827',
						'--tw-prose-quote-borders': '#e5e7eb',
						'--tw-prose-captions': '#6b7280',
						'--tw-prose-code': '#111827',
						'--tw-prose-pre-code': '#e5e7eb',
						'--tw-prose-pre-bg': '#1f2937',
						'--tw-prose-th-borders': '#d1d5db',
						'--tw-prose-td-borders': '#e5e7eb',
						fontSize: '1rem',
						lineHeight: '1.75',
						maxWidth: 'none'
					}
				},
				invert: {
					css: {
						'--tw-prose-body': '#d1d5db',
						'--tw-prose-headings': '#fff',
						'--tw-prose-lead': '#9ca3af',
						'--tw-prose-links': '#fff',
						'--tw-prose-bold': '#fff',
						'--tw-prose-counters': '#9ca3af',
						'--tw-prose-bullets': '#4b5563',
						'--tw-prose-hr': '#374151',
						'--tw-prose-quotes': '#f3f4f6',
						'--tw-prose-quote-borders': '#374151',
						'--tw-prose-captions': '#9ca3af',
						'--tw-prose-code': '#fff',
						'--tw-prose-pre-code': '#d1d5db',
						'--tw-prose-pre-bg': '#0f172a',
						'--tw-prose-th-borders': '#4b5563',
						'--tw-prose-td-borders': '#374151'
					}
				}
			},
			padding: {
				'safe-bottom': 'env(safe-area-inset-bottom)'
			},
			transitionProperty: {
				width: 'width'
			}
		}
	},
	plugins: [typography, containerQueries]
};
