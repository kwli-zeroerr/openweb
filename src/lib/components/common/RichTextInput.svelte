<script lang="ts">
	import { marked } from 'marked';
	marked.use({
		breaks: true,
		gfm: true,
		renderer: {
			list(body, ordered, start) {
				const type = ordered ? 'ol' : 'ul';
				const startatt = ordered && start !== 1 ? ` start="${start}"` : '';
				return `<${type}${startatt}>${body}</${type}>`;
			},

			listitem(text) {
				return `<li>${text}</li>`;
			}
		}
	});

	import TurndownService from 'turndown';
	import { gfm } from '@joplin/turndown-plugin-gfm';
	const turndownService = new TurndownService({
		codeBlockStyle: 'fenced',
		headingStyle: 'atx'
	});
	turndownService.escape = (string) => string;

	// Use turndown-plugin-gfm for proper GFM table support
	turndownService.use(gfm);

	// Add custom table header rule before using GFM plugin
	turndownService.addRule('tableHeaders', {
		filter: 'th',
		replacement: function (content, node) {
			return content;
		}
	});

	// Add custom table rule to handle headers properly
	turndownService.addRule('tables', {
		filter: 'table',
		replacement: function (content, node) {
			// Extract rows
			const rows = Array.from(node.querySelectorAll('tr'));
			if (rows.length === 0) return content;

			let markdown = '\n';

			rows.forEach((row, rowIndex) => {
				const cells = Array.from(row.querySelectorAll('th, td'));
				const cellContents = cells.map((cell) => {
					// Get the text content and clean it up
					let cellContent = turndownService.turndown(cell.innerHTML).trim();
					// Remove extra paragraph tags that might be added
					cellContent = cellContent.replace(/^\n+|\n+$/g, '');
					return cellContent;
				});

				// Add the row
				markdown += '| ' + cellContents.join(' | ') + ' |\n';

				// Add separator after first row (which should be headers)
				if (rowIndex === 0) {
					const separator = cells.map(() => '---').join(' | ');
					markdown += '| ' + separator + ' |\n';
				}
			});

			return markdown + '\n';
		}
	});

	// Convert TipTap mention spans -> <@id>
	turndownService.addRule('mentions', {
		filter: (node) => node.nodeName === 'SPAN' && node.getAttribute('data-type') === 'mention',
		replacement: (_content, node: HTMLElement) => {
			const id = node.getAttribute('data-id') || '';
			// TipTap stores the trigger char in data-mention-suggestion-char (usually "@")
			const ch = node.getAttribute('data-mention-suggestion-char') || '@';
			// Emit <@id> style, e.g. <@llama3.2:latest>
			return `<${ch}${id}>`;
		}
	});

	import { onMount, onDestroy, tick, getContext } from 'svelte';
	import { createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const eventDispatch = createEventDispatcher();

	import { Fragment, DOMParser } from 'prosemirror-model';
	import { EditorState, Plugin, PluginKey, TextSelection, Selection } from 'prosemirror-state';
	import { Decoration, DecorationSet } from 'prosemirror-view';
	import { Editor, Extension, mergeAttributes } from '@tiptap/core';

	import { AIAutocompletion } from './RichTextInput/AutoCompletion.js';

	import StarterKit from '@tiptap/starter-kit';

	// Bubble and Floating menus are currently fixed to v2 due to styling issues in v3
	// TODO: Update to v3 when styling issues are resolved
	import BubbleMenu from '@tiptap/extension-bubble-menu';
	import FloatingMenu from '@tiptap/extension-floating-menu';

	import { TableKit } from '@tiptap/extension-table';
	import { ListKit } from '@tiptap/extension-list';
	import { Placeholder, CharacterCount } from '@tiptap/extensions';

	import Image from './RichTextInput/Image/index.js';
	// import TiptapImage from '@tiptap/extension-image';

	import FileHandler from '@tiptap/extension-file-handler';
	import Typography from '@tiptap/extension-typography';
	import Highlight from '@tiptap/extension-highlight';
	import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';

	import Mention from '@tiptap/extension-mention';
	import FormattingButtons from './RichTextInput/FormattingButtons.svelte';
	import TableContextMenu from './RichTextInput/TableContextMenu.svelte';

	import { PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';
	import { createLowlight } from 'lowlight';
	import hljs from 'highlight.js';

	import type { SocketIOCollaborationProvider } from './RichTextInput/Collaboration';

	export let oncompositionstart = (e) => {};
	export let oncompositionend = (e) => {};
	export let onChange = (e) => {};

	// create a lowlight instance with all languages loaded
	const lowlight = createLowlight(
		hljs.listLanguages().reduce(
			(obj, lang) => {
				obj[lang] = () => hljs.getLanguage(lang);
				return obj;
			},
			{} as Record<string, any>
		)
	);

	export let editor: Editor | null = null;

	export let socket = null;
	export let user = null;
	export let files = [];

	export let documentId = '';

	export let className = 'input-prose';
	export let placeholder = $i18n.t('Type here...');
	let _placeholder = placeholder;

	$: if (placeholder !== _placeholder) {
		setPlaceholder();
	}

	const setPlaceholder = () => {
		_placeholder = placeholder;
		if (editor) {
			editor?.view.dispatch(editor.state.tr);
		}
	};

	export let richText = true;
	export let dragHandle = false;
	export let link = false;
	export let image = false;
	export let fileHandler = false;
	export let suggestions = null;

	export let onFileDrop = (currentEditor, files, pos) => {
		files.forEach((file) => {
			const fileReader = new FileReader();

			fileReader.readAsDataURL(file);
			fileReader.onload = () => {
				currentEditor
					.chain()
					.insertContentAt(pos, {
						type: 'image',
						attrs: {
							src: fileReader.result
						}
					})
					.focus()
					.run();
			};
		});
	};

	export let onFilePaste = (currentEditor, files, htmlContent) => {
		files.forEach((file) => {
			if (htmlContent) {
				// if there is htmlContent, stop manual insertion & let other extensions handle insertion via inputRule
				// you could extract the pasted file from this url string and upload it to a server for example
				console.log(htmlContent); // eslint-disable-line no-console
				return false;
			}

			const fileReader = new FileReader();

			fileReader.readAsDataURL(file);
			fileReader.onload = () => {
				currentEditor
					.chain()
					.insertContentAt(currentEditor.state.selection.anchor, {
						type: 'image',
						attrs: {
							src: fileReader.result
						}
					})
					.focus()
					.run();
			};
		});
	};

	export let onSelectionUpdate = (e) => {};

	export let id = '';
	export let value = '';
	export let html = '';

	export let json = false;
	export let raw = false;
	export let editable = true;
	export let collaboration = false;

	export let showFormattingToolbar = true;
	export let fixedToolbar = false; // 是否使用固定工具栏（嵌入在编辑器下方）
	export let toolbarPosition: 'top' | 'bottom' = 'bottom'; // 工具栏位置：顶部或底部

	export let preserveBreaks = false;
	export let generateAutoCompletion: Function = async () => null;
	export let autocomplete = false;
	export let messageInput = false;
	export let shiftEnter = false;
	export let largeTextAsFile = false;
	export let insertPromptAsRichText = false;
	export let floatingMenuPlacement = 'bottom-start';

	let content = null;
	let htmlValue = '';
	let jsonValue = '';
	let mdValue = '';

	let provider: SocketIOCollaborationProvider | null = null;

	let floatingMenuElement: Element | null = null;
	let bubbleMenuElement: Element | null = null;
	let element: Element | null = null;
	
	// 表格右键菜单状态
	let tableContextMenuVisible = false;
	let tableContextMenuX = 0;
	let tableContextMenuY = 0;
	
	// 格式刷状态
	let formatPainterActive = false;
	let copiedCellFormat: {
		backgroundColor?: string;
		color?: string;
		textAlign?: string;
		fontWeight?: string;
		fontStyle?: string;
		border?: string;
		padding?: string;
	} | null = null;

	const options = {
		throwOnError: false
	};

	$: if (editor) {
		editor.setOptions({
			editable: editable
		});
	}
	
	// 应用格式到单元格
	const applyFormatToCell = (cell: HTMLElement, format: typeof copiedCellFormat) => {
		if (!format) return;
		
		// 应用样式
		if (format.backgroundColor && format.backgroundColor !== 'rgba(0, 0, 0, 0)' && format.backgroundColor !== 'transparent') {
			cell.style.backgroundColor = format.backgroundColor;
		}
		if (format.color) {
			cell.style.color = format.color;
		}
		if (format.textAlign) {
			cell.style.textAlign = format.textAlign;
		}
		if (format.fontWeight) {
			cell.style.fontWeight = format.fontWeight;
		}
		if (format.fontStyle) {
			cell.style.fontStyle = format.fontStyle;
		}
		if (format.border) {
			cell.style.border = format.border;
		}
		if (format.padding) {
			cell.style.padding = format.padding;
		}
	};
	
	// 全局点击事件监听，关闭表格右键菜单和处理格式刷
	onMount(() => {
		if (typeof window !== 'undefined') {
			const handleGlobalClick = (event: MouseEvent) => {
				if (tableContextMenuVisible) {
					const target = event.target as HTMLElement;
					// 如果点击的不是菜单本身，关闭菜单
					if (!target.closest('.table-context-menu')) {
						tableContextMenuVisible = false;
					}
				}
			};
			
			const handleFormatPainterToggle = (event: CustomEvent) => {
				formatPainterActive = event.detail.active;
				if (!formatPainterActive) {
					copiedCellFormat = null;
				}
			};
			
			window.addEventListener('click', handleGlobalClick);
			window.addEventListener('toggleFormatPainter', handleFormatPainterToggle as EventListener);
			
			return () => {
				window.removeEventListener('click', handleGlobalClick);
				window.removeEventListener('toggleFormatPainter', handleFormatPainterToggle as EventListener);
			};
		}
	});

	$: if (value === null && html !== null && editor) {
		editor.commands.setContent(html);
	}

	export const getWordAtDocPos = () => {
		if (!editor) return '';
		const { state } = editor.view;
		const pos = state.selection.from;
		const doc = state.doc;
		const resolvedPos = doc.resolve(pos);
		const textBlock = resolvedPos.parent;
		const paraStart = resolvedPos.start();
		const text = textBlock.textContent;
		const offset = resolvedPos.parentOffset;

		let wordStart = offset,
			wordEnd = offset;
		while (wordStart > 0 && !/\s/.test(text[wordStart - 1])) wordStart--;
		while (wordEnd < text.length && !/\s/.test(text[wordEnd])) wordEnd++;

		const word = text.slice(wordStart, wordEnd);

		return word;
	};

	// Returns {start, end} of the word at pos
	function getWordBoundsAtPos(doc, pos) {
		const resolvedPos = doc.resolve(pos);
		const textBlock = resolvedPos.parent;
		const paraStart = resolvedPos.start();
		const text = textBlock.textContent;

		const offset = resolvedPos.parentOffset;
		let wordStart = offset,
			wordEnd = offset;
		while (wordStart > 0 && !/\s/.test(text[wordStart - 1])) wordStart--;
		while (wordEnd < text.length && !/\s/.test(text[wordEnd])) wordEnd++;
		return {
			start: paraStart + wordStart,
			end: paraStart + wordEnd
		};
	}

	export const replaceCommandWithText = async (text) => {
		const { state, dispatch } = editor.view;
		const { selection } = state;
		const pos = selection.from;

		// Get the plain text of this document
		// const docText = state.doc.textBetween(0, state.doc.content.size, '\n', '\n');

		// Find the word boundaries at cursor
		const { start, end } = getWordBoundsAtPos(state.doc, pos);

		let tr = state.tr;

		if (insertPromptAsRichText) {
			const htmlContent = marked
				.parse(text, {
					breaks: true,
					gfm: true
				})
				.trim();

			// Create a temporary div to parse HTML
			const tempDiv = document.createElement('div');
			tempDiv.innerHTML = htmlContent;

			// Convert HTML to ProseMirror nodes
			const fragment = DOMParser.fromSchema(state.schema).parse(tempDiv);

			// Extract just the content, not the wrapper paragraphs
			const content = fragment.content;
			let nodesToInsert = [];

			content.forEach((node) => {
				if (node.type.name === 'paragraph') {
					// If it's a paragraph, extract its content
					nodesToInsert.push(...node.content.content);
				} else {
					nodesToInsert.push(node);
				}
			});

			tr = tr.replaceWith(start, end, nodesToInsert);
			// Calculate new position
			const newPos = start + nodesToInsert.reduce((sum, node) => sum + node.nodeSize, 0);
			tr = tr.setSelection(Selection.near(tr.doc.resolve(newPos)));
		} else {
			if (text.includes('\n')) {
				// Split the text into lines and create a <p> node for each line
				const lines = text.split('\n');
				const nodes = lines.map(
					(line, index) =>
						index === 0
							? state.schema.text(line ? line : []) // First line is plain text
							: state.schema.nodes.paragraph.create({}, line ? state.schema.text(line) : undefined) // Subsequent lines are paragraphs
				);

				// Build and dispatch the transaction to replace the word at cursor
				tr = tr.replaceWith(start, end, nodes);

				let newSelectionPos;

				// +1 because the insert happens at start, so last para starts at (start + sum of all previous nodes' sizes)
				let lastPos = start;
				for (let i = 0; i < nodes.length; i++) {
					lastPos += nodes[i].nodeSize;
				}
				// Place cursor inside the last paragraph at its end
				newSelectionPos = lastPos;

				tr = tr.setSelection(TextSelection.near(tr.doc.resolve(newSelectionPos)));
			} else {
				tr = tr.replaceWith(
					start,
					end, // replace this range
					text !== '' ? state.schema.text(text) : []
				);

				tr = tr.setSelection(
					state.selection.constructor.near(tr.doc.resolve(start + text.length + 1))
				);
			}
		}

		dispatch(tr);

		await tick();
		// selectNextTemplate(state, dispatch);
	};

	export const setText = (text: string) => {
		if (!editor) return;
		text = text.replaceAll('\n\n', '\n');

		// reset the editor content
		editor.commands.clearContent();

		const { state, view } = editor;
		const { schema, tr } = state;

		if (text.includes('\n')) {
			// Multiple lines: make paragraphs
			const lines = text.split('\n');
			// Map each line to a paragraph node (empty lines -> empty paragraph)
			const nodes = lines.map((line) =>
				schema.nodes.paragraph.create({}, line ? schema.text(line) : undefined)
			);
			// Create a document fragment containing all parsed paragraphs
			const fragment = Fragment.fromArray(nodes);
			// Replace current selection with these paragraphs
			tr.replaceSelectionWith(fragment, false /* don't select new */);
			view.dispatch(tr);
		} else if (text === '') {
			// Empty: replace with empty paragraph using tr
			editor.commands.clearContent();
		} else {
			// Single line: create paragraph with text
			const paragraph = schema.nodes.paragraph.create({}, schema.text(text));
			tr.replaceSelectionWith(paragraph, false);
			view.dispatch(tr);
		}

		selectNextTemplate(editor.view.state, editor.view.dispatch);
		focus();
	};

	export const insertContent = (content) => {
		if (!editor) return;
		const { state, view } = editor;
		const { schema, tr } = state;

		// If content is a string, convert it to a ProseMirror node
		const htmlContent = marked.parse(content);

		// insert the HTML content at the current selection
		editor.commands.insertContent(htmlContent);

		focus();
	};

	export const replaceVariables = (variables) => {
		if (!editor) return;
		const { state, view } = editor;
		const { doc } = state;

		// Create a transaction to replace variables
		let tr = state.tr;
		let offset = 0; // Track position changes due to text length differences

		// Collect all replacements first to avoid position conflicts
		const replacements = [];

		doc.descendants((node, pos) => {
			if (node.isText && node.text) {
				const text = node.text;
				const replacedText = text.replace(/{{\s*([^|}]+)(?:\|[^}]*)?\s*}}/g, (match, varName) => {
					const trimmedVarName = varName.trim();
					return variables.hasOwnProperty(trimmedVarName)
						? String(variables[trimmedVarName])
						: match;
				});

				if (replacedText !== text) {
					replacements.push({
						from: pos,
						to: pos + text.length,
						text: replacedText
					});
				}
			}
		});

		// Apply replacements in reverse order to maintain correct positions
		replacements.reverse().forEach(({ from, to, text }) => {
			tr = tr.replaceWith(from, to, text !== '' ? state.schema.text(text) : []);
		});

		// Only dispatch if there are changes
		if (replacements.length > 0) {
			view.dispatch(tr);
		}
	};

	export const focus = () => {
		if (editor) {
			try {
				editor.view?.focus();
				// 不自动滚动，避免干扰用户滚动位置
				// editor.view?.dispatch(editor.view.state.tr.scrollIntoView());
			} catch (e) {
				// sometimes focusing throws an error, ignore
				console.warn('Error focusing editor', e);
			}
		}
	};

	// Function to find the next template in the document
	function findNextTemplate(doc, from = 0) {
		const patterns = [{ start: '{{', end: '}}' }];

		let result = null;

		doc.nodesBetween(from, doc.content.size, (node, pos) => {
			if (result) return false; // Stop if we've found a match
			if (node.isText) {
				const text = node.text;
				let index = Math.max(0, from - pos);
				while (index < text.length) {
					for (const pattern of patterns) {
						if (text.startsWith(pattern.start, index)) {
							const endIndex = text.indexOf(pattern.end, index + pattern.start.length);
							if (endIndex !== -1) {
								result = {
									from: pos + index,
									to: pos + endIndex + pattern.end.length
								};
								return false; // Stop searching
							}
						}
					}
					index++;
				}
			}
		});

		return result;
	}

	// Function to select the next template in the document
	function selectNextTemplate(state, dispatch) {
		const { doc, selection } = state;
		const from = selection.to;
		let template = findNextTemplate(doc, from);

		if (!template) {
			// If not found, search from the beginning
			template = findNextTemplate(doc, 0);
		}

		if (template) {
			if (dispatch) {
				const tr = state.tr.setSelection(TextSelection.create(doc, template.from, template.to));
				// 不自动滚动，避免干扰用户滚动位置
				dispatch(tr.setMeta('preventScroll', true));
			}
			return true;
		}
		return false;
	}

	export const setContent = (content) => {
		editor.commands.setContent(content);
	};

	const selectTemplate = () => {
		// 只在 messageInput 模式下执行模板选择
		if (!messageInput) {
			return;
		}
		
		if (value !== '') {
			// After updating the state, try to find and select the next template
			setTimeout(() => {
				const templateFound = selectNextTemplate(editor.view.state, editor.view.dispatch);
				if (!templateFound) {
					// 只在 messageInput 模式下才跳转到末尾
					if (messageInput) {
						editor.commands.focus('end');
					}
				}
			}, 0);
		}
	};

	const SelectionDecoration = Extension.create({
		name: 'selectionDecoration',
		addProseMirrorPlugins() {
			return [
				new Plugin({
					key: new PluginKey('selection'),
					props: {
						decorations: (state) => {
							const { selection } = state;
							const { focused } = this.editor;

							if (focused || selection.empty) {
								return null;
							}

							return DecorationSet.create(state.doc, [
								Decoration.inline(selection.from, selection.to, {
									class: 'editor-selection'
								})
							]);
						}
					}
				})
			];
		}
	});

	import { listDragHandlePlugin } from './RichTextInput/listDragHandlePlugin.js';

	const ListItemDragHandle = Extension.create({
		name: 'listItemDragHandle',
		addProseMirrorPlugins() {
			return [
				listDragHandlePlugin({
					itemTypeNames: ['listItem'],
					getEditor: () => this.editor
				})
			];
		}
	});

	onMount(async () => {
		content = value;

		if (json) {
			if (!content) {
				content = html ? html : null;
			}
		} else {
			if (preserveBreaks) {
				turndownService.addRule('preserveBreaks', {
					filter: 'br', // Target <br> elements
					replacement: function (content) {
						return '<br/>';
					}
				});
			}

			if (!raw) {
				async function tryParse(value, attempts = 3, interval = 100) {
					try {
						// Try parsing the value
						return marked.parse(value.replaceAll(`\n<br/>`, `<br/>`), {
							breaks: false
						});
					} catch (error) {
						// If no attempts remain, fallback to plain text
						if (attempts <= 1) {
							return value;
						}
						// Wait for the interval, then retry
						await new Promise((resolve) => setTimeout(resolve, interval));
						return tryParse(value, attempts - 1, interval); // Recursive call
					}
				}

				// Usage example
				content = await tryParse(value);
			}
		}

		console.log('content', content);

		if (collaboration && documentId && socket && user) {
			const { SocketIOCollaborationProvider } = await import('./RichTextInput/Collaboration');
			provider = new SocketIOCollaborationProvider(documentId, socket, user, content);
		}

		console.log(bubbleMenuElement, floatingMenuElement);
		console.log(suggestions);

		editor = new Editor({
			element: element,
			extensions: [
				StarterKit.configure({
					link: link
				}),
				...(dragHandle ? [ListItemDragHandle] : []),
				Placeholder.configure({ placeholder: () => _placeholder, showOnlyWhenEditable: false }),
				SelectionDecoration,

				...(richText
					? [
							CodeBlockLowlight.configure({
								lowlight
							}),
							Highlight,
							Typography,
						TableKit.configure({
							table: { 
								resizable: false, // 禁用表格大小调整，防止拖动滚动
								HTMLAttributes: {
									class: 'table-wrapper',
									style: 'overflow: visible; touch-action: none;'
								}
							},
							tableCell: {
								HTMLAttributes: {
									class: 'table-cell'
								}
							},
							tableRow: {
								HTMLAttributes: {
									class: 'table-row'
								}
							}
						}),
							ListKit.configure({})
						]
					: []),
				...(suggestions
					? [
							Mention.configure({
								HTMLAttributes: { class: 'mention' },
								suggestions: suggestions
							})
						]
					: []),

				CharacterCount.configure({}),
				...(image ? [Image] : []),
				...(fileHandler
					? [
							FileHandler.configure({
								onDrop: onFileDrop,
								onPaste: onFilePaste
							})
						]
					: []),
				...(richText && autocomplete
					? [
							AIAutocompletion.configure({
								generateCompletion: async (text) => {
									if (text.trim().length === 0) {
										return null;
									}

									const suggestion = await generateAutoCompletion(text).catch(() => null);
									if (!suggestion || suggestion.trim().length === 0) {
										return null;
									}

									return suggestion;
								}
							})
						]
					: []),
				...(richText && showFormattingToolbar && !fixedToolbar
					? [
							BubbleMenu.configure({
								element: bubbleMenuElement,
								tippyOptions: {
									duration: 100,
									arrow: false,
									placement: 'top',
									theme: 'transparent',
									offset: [0, 2],
									popperOptions: {
										strategy: 'fixed',
										modifiers: [
											{
												name: 'preventOverflow',
												options: {
													boundary: 'viewport',
													altAxis: true,
													tether: true,
													padding: 8
												}
											},
											{
												name: 'flip',
												options: {
													boundary: 'viewport',
													fallbackPlacements: ['bottom', 'top-start', 'top-end', 'bottom-start', 'bottom-end']
												}
											}
										]
									}
								}
							}),
							FloatingMenu.configure({
								element: floatingMenuElement,
								tippyOptions: {
									duration: 100,
									arrow: false,
									placement: floatingMenuPlacement,
									theme: 'transparent',
									offset: [-12, 4],
									popperOptions: {
										strategy: 'fixed',
										modifiers: [
											{
												name: 'preventOverflow',
												options: {
													boundary: 'viewport',
													altAxis: true,
													tether: true,
													padding: 16,
													rootBoundary: 'viewport'
												}
											},
											{
												name: 'flip',
												options: {
													boundary: 'viewport',
													rootBoundary: 'viewport',
													fallbackPlacements: ['bottom-start', 'top-start', 'bottom-end', 'top-end']
												}
											},
											{
												name: 'computeStyles',
												options: {
													adaptive: true,
													roundOffsets: true
												}
											}
										]
									}
								}
							})
						]
					: []),
				...(collaboration && provider ? [provider.getEditorExtension()] : [])
			],
			content: collaboration ? undefined : content,
			autofocus: messageInput ? true : false,
			onTransaction: () => {
				// force re-render so `editor.isActive` works as expected
				editor = editor;
				if (!editor) return;

				htmlValue = editor.getHTML();
				jsonValue = editor.getJSON();
				mdValue = turndownService
					.turndown(
						htmlValue
							.replace(/<p><\/p>/g, '<br/>')
							.replace(/ {2,}/g, (m) => m.replace(/ /g, '\u00a0'))
					)
					.replace(/\u00a0/g, ' ');

				onChange({
					html: htmlValue,
					json: jsonValue,
					md: mdValue
				});

				if (json) {
					value = jsonValue;
				} else {
					if (raw) {
						value = htmlValue;
					} else {
						if (!preserveBreaks) {
							mdValue = mdValue.replace(/<br\/>/g, '');
						}

						if (value !== mdValue) {
							value = mdValue;

							// check if the node is paragraph as well
							if (editor.isActive('paragraph')) {
								if (value === '') {
									editor.commands.clearContent();
								}
							}
						}
					}
				}
			},
			editorProps: {
				attributes: { id },
				handlePaste: (view, event) => {
					// Force plain-text pasting when richText === false
					if (!richText) {
						// swallow HTML completely
						event.preventDefault();
						const { state, dispatch } = view;

						const plainText = (event.clipboardData?.getData('text/plain') ?? '').replace(
							/\r\n/g,
							'\n'
						);

						const lines = plainText.split('\n');
						const nodes = [];

						lines.forEach((line, index) => {
							if (index > 0) {
								nodes.push(state.schema.nodes.hardBreak.create());
							}
							if (line.length > 0) {
								nodes.push(state.schema.text(line));
							}
						});

						const fragment = Fragment.fromArray(nodes);
						// 不自动滚动，避免干扰用户滚动位置
						dispatch(state.tr.replaceSelectionWith(fragment, false));

						return true; // handled
					}

					return false;
				},
				handleDOMEvents: {
					compositionstart: (view, event) => {
						oncompositionstart(event);
						return false;
					},
					compositionend: (view, event) => {
						oncompositionend(event);
						return false;
					},
					focus: (view, event) => {
						eventDispatch('focus', { event });
						return false;
					},
					keyup: (view, event) => {
						eventDispatch('keyup', { event });
						return false;
					},
					// 阻止表格内的滚动事件
					wheel: (view, event) => {
						const target = event.target as HTMLElement;
						// 如果事件发生在表格内，阻止默认滚动行为
						if (target.closest('table')) {
							// 允许正常的文本选择，但阻止表格整体滚动
							const table = target.closest('table');
							if (table && (target.tagName === 'TABLE' || target === table)) {
								event.preventDefault();
								return true;
							}
						}
						return false;
					},
					// 阻止表格内的触摸滚动
					touchstart: (view, event) => {
						const target = event.target as HTMLElement;
						if (target.tagName === 'TABLE' || (target.closest('table') && target.tagName !== 'TD' && target.tagName !== 'TH')) {
							event.preventDefault();
							return true;
						}
						return false;
					},
					touchmove: (view, event) => {
						const target = event.target as HTMLElement;
						if (target.tagName === 'TABLE' || (target.closest('table') && target.tagName !== 'TD' && target.tagName !== 'TH')) {
							event.preventDefault();
							return true;
						}
						return false;
					},
					contextmenu: (view, event) => {
						// 如果格式刷激活，不显示右键菜单
						if (formatPainterActive) {
							return false;
						}
						
						// 检查是否在表格内
						const { state } = view;
						const { $head } = state.selection;
						
						// 检查当前节点或父节点是否是表格相关节点
						let currentNode = $head;
						let isInTable = false;
						
						while (currentNode) {
							const nodeType = currentNode.parent.type.name;
							if (nodeType === 'table' || nodeType === 'tableRow' || nodeType === 'tableCell' || nodeType === 'tableHeader') {
								isInTable = true;
								break;
							}
							if (!currentNode.depth) break;
							currentNode = state.doc.resolve(currentNode.before());
						}
						
						if (isInTable && editable) {
							event.preventDefault();
							event.stopPropagation();
							tableContextMenuX = (event as MouseEvent).clientX;
							tableContextMenuY = (event as MouseEvent).clientY;
							tableContextMenuVisible = true;
							return true;
						}
						
						return false;
					},
					mousedown: (view, event) => {
						// 格式刷处理（优先处理，但只在激活时执行）
						if (formatPainterActive) {
							const target = event.target as HTMLElement;
							const cell = target.closest('td, th') as HTMLElement;
							
							if (cell) {
								// 如果还没有复制格式，则复制当前单元格的格式
								if (!copiedCellFormat) {
									const computedStyle = window.getComputedStyle(cell);
									copiedCellFormat = {
										backgroundColor: computedStyle.backgroundColor,
										color: computedStyle.color,
										textAlign: computedStyle.textAlign,
										fontWeight: computedStyle.fontWeight,
										fontStyle: computedStyle.fontStyle,
										border: computedStyle.border,
										padding: computedStyle.padding
									};
									// 高亮显示已复制的单元格
									cell.style.outline = '2px dashed #3b82f6';
									cell.style.outlineOffset = '-2px';
									setTimeout(() => {
										cell.style.outline = '';
										cell.style.outlineOffset = '';
									}, 1000);
									event.preventDefault();
									event.stopPropagation();
									return true;
								} else {
									// 应用格式到目标单元格
									applyFormatToCell(cell, copiedCellFormat);
									
									const table = target.closest('table');
									const row = target.closest('tr');
									const mouseEvent = event as MouseEvent;
									
									// 如果按住 Shift，应用到整行
									if (mouseEvent.shiftKey && row) {
										const rowCells = row.querySelectorAll('td, th');
										rowCells.forEach(c => applyFormatToCell(c as HTMLElement, copiedCellFormat));
									}
									// 如果按住 Ctrl/Cmd，应用到整列
									else if ((mouseEvent.ctrlKey || mouseEvent.metaKey) && table && row) {
										const cellIndex = Array.from(row.querySelectorAll('td, th')).indexOf(cell);
										if (cellIndex >= 0) {
											const allRows = table.querySelectorAll('tr');
											allRows.forEach(r => {
												const cells = r.querySelectorAll('td, th');
												if (cells[cellIndex]) {
													applyFormatToCell(cells[cellIndex] as HTMLElement, copiedCellFormat);
												}
											});
										}
									}
									
									// 重置格式刷状态
									copiedCellFormat = null;
									formatPainterActive = false;
									window.dispatchEvent(new CustomEvent('formatPainterApplied'));
									event.preventDefault();
									event.stopPropagation();
									return true;
								}
							}
						}
						
						// 只在必要时检查表格相关事件（优化性能）
						const target = event.target as HTMLElement;
						
						// 如果点击的是表格本身（不是单元格内容），阻止拖动
						if (target.tagName === 'TABLE') {
							event.preventDefault();
							event.stopPropagation();
							return true;
						}
						
						// 快速检查是否在表格内
						const tableElement = target.closest('table');
						if (tableElement) {
							// 如果点击的是表格容器或表格边框，也阻止拖动
							if (target === tableElement || target.classList.contains('table-wrapper')) {
								event.preventDefault();
								event.stopPropagation();
								return true;
							}
							// 单元格内的点击允许正常编辑，不阻止
						}
						
						return false;
					},
					// 阻止表格内的滚轮事件（只阻止表格本身的滚动，不影响单元格内容）
					wheel: (view, event) => {
						const target = event.target as HTMLElement;
						const table = target.closest('table');
						
						if (table) {
							// 如果滚轮事件发生在表格本身（不是单元格内容），阻止默认滚动
							if (target.tagName === 'TABLE' || target === table) {
								event.preventDefault();
								event.stopPropagation();
								return true;
							}
							// 允许单元格内的正常滚动（如果有滚动条）
						}
						
						return false;
					},
					keydown: (view, event) => {
						if (messageInput) {
							// Check if the current selection is inside a structured block (like codeBlock or list)
							const { state } = view;
							const { $head } = state.selection;

							// Recursive function to check ancestors for specific node types
							function isInside(nodeTypes: string[]): boolean {
								let currentNode = $head;
								// 检查所有父节点
								while (currentNode) {
									// 检查当前节点的父节点类型
									if (nodeTypes.includes(currentNode.parent.type.name)) {
										return true;
									}
									// 检查当前节点前后的节点类型（用于检查是否在 taskItem 等节点内）
									if (currentNode.nodeAfter && nodeTypes.includes(currentNode.nodeAfter.type.name)) {
										return true;
									}
									if (currentNode.nodeBefore && nodeTypes.includes(currentNode.nodeBefore.type.name)) {
										return true;
									}
									if (!currentNode.depth) break; // Stop if we reach the top
									currentNode = state.doc.resolve(currentNode.before()); // Move to the parent node
								}
								return false;
							}

							// 在列表中，让 ProseMirror 处理所有按键，不要执行任何自定义逻辑
							const isInList = isInside(['listItem', 'bulletList', 'orderedList']);
							if (isInList && (event.key !== 'Tab' && event.key !== 'Escape')) {
								// Tab 和 Escape 键需要特殊处理，其他按键都让 ProseMirror 处理
								return false;
							}

							// Handle Tab Key
							if (event.key === 'Tab') {
								const isInCodeBlock = isInside(['codeBlock']);

								if (isInCodeBlock) {
									// Handle tab in code block - insert tab character or spaces
									const tabChar = '\t'; // or '    ' for 4 spaces
									editor.commands.insertContent(tabChar);
									event.preventDefault();
									return true; // Prevent further propagation
								} else {
									const handled = selectNextTemplate(view.state, view.dispatch);
									if (handled) {
										event.preventDefault();
										return true;
									}
								}
							}

							if (event.key === 'Enter') {
								const isCtrlPressed = event.ctrlKey || event.metaKey; // metaKey is for Cmd key on Mac

								const { state } = view;
								const selection = state.selection;
								const fromPos = selection.$from; // 避免使用 $from 作为变量名，防止 Svelte 误认为它是 store
								const lineStart = fromPos.before(fromPos.depth);
								const lineEnd = fromPos.after(fromPos.depth);
								const lineText = state.doc.textBetween(lineStart, lineEnd, '\n', '\0').trim();
								if (event.shiftKey && !isCtrlPressed) {
									if (lineText.startsWith('```')) {
										// Fix GitHub issue #16337: prevent backtick removal for lines starting with ```
										return false; // Let ProseMirror handle the Enter key normally
									}

									editor.commands.enter(); // Insert a new line
									// 不自动滚动，避免干扰用户滚动位置
									// view.dispatch(view.state.tr.scrollIntoView()); // Move viewport to the cursor
									event.preventDefault();
									return true;
								} else {
									const isInCodeBlock = isInside(['codeBlock']);
									// 检查是否在列表中
									const isInList = isInside(['listItem', 'bulletList', 'orderedList']);
									const isInHeading = isInside(['heading']);

									console.log({ isInCodeBlock, isInList, isInHeading });

									if (isInCodeBlock || isInList || isInHeading) {
										// Let ProseMirror handle the normal Enter behavior
										return false;
									}

									const suggestionsElement = document.getElementById('suggestions-container');
									if (lineText.startsWith('#') && suggestionsElement) {
										console.log('Letting heading suggestion handle Enter key');
										return true;
									}
									
									// 在列表中，完全让 ProseMirror 处理，不要执行任何自定义逻辑
									if (isInList) {
										return false;
									}
									
									// 检查光标前面是否有两个空格，如果有则先删除它们，避免 Markdown 硬换行导致光标位置异常
									const { from } = state.selection;
									if (from >= 2) {
										const textBefore = state.doc.textBetween(from - 2, from, '', '');
										if (textBefore === '  ') {
											// 如果前面有两个空格，删除它们并手动创建新段落
											const newFrom = from - 2;
											// 获取当前段落节点位置
											const $pos = state.doc.resolve(newFrom);
											
											// 在一个事务中完成：删除空格并分割段落
											const tr = state.tr
												.delete(from - 2, from)
												.split($pos.pos, 1);
											
											// 设置光标到新段落开头
											const newPos = tr.doc.resolve(newFrom);
											tr.setSelection(TextSelection.near(newPos));
											
											view.dispatch(tr);
											event.preventDefault();
											return true;
										}
									}
									
									// 检查光标是否在行首，如果是，确保换行后不会添加空格
									// lineStart 已经在上面声明过了，直接使用
									const isAtLineStart = from === lineStart || (from === lineStart + 1 && state.doc.textBetween(lineStart, from, '', '') === ' ');
									
									if (isAtLineStart) {
										// 光标在行首，手动处理换行，确保新行开头没有空格
										// 直接分割段落，不添加任何内容
										const tr = state.tr.split(fromPos.pos, 1);
										view.dispatch(tr);
										
										// 在下一个事件循环中检查新行开头是否有空格并删除
										// 使用闭包保存 view 引用，避免在回调中访问 editor
										const currentView = view;
										requestAnimationFrame(() => {
											const newState = currentView.state;
											const newSelection = newState.selection;
											const newFrom = newSelection.from;
											
											// 检查新行开头是否有空格
											if (newFrom < newState.doc.content.size) {
												const textAfter = newState.doc.textBetween(newFrom, Math.min(newFrom + 2, newState.doc.content.size), '', '');
												if (textAfter === '  ' || textAfter.startsWith(' ')) {
													// 删除新行开头的空格
													const spaceCount = textAfter.match(/^ +/)?.[0].length || 0;
													if (spaceCount > 0) {
														const tr = newState.tr.delete(newFrom, newFrom + spaceCount);
														currentView.dispatch(tr);
														// 确保光标位置正确
														currentView.focus();
													}
												}
											}
										});
										
										event.preventDefault();
										return true;
									}
									
									// 让 ProseMirror 处理默认的换行行为
									return false;
								}
							}

							// Handle shift + Enter for a line break
							if (shiftEnter) {
								if (event.key === 'Enter' && event.shiftKey && !event.ctrlKey && !event.metaKey) {
									editor.commands.setHardBreak(); // Insert a hard break
									// 不自动滚动，避免干扰用户滚动位置
									// view.dispatch(view.state.tr.scrollIntoView()); // Move viewport to the cursor
									event.preventDefault();
									return true;
								}
							}
						}
						eventDispatch('keydown', { event });
						return false;
					},
					paste: (view, event) => {
						if (event.clipboardData) {
							const plainText = event.clipboardData.getData('text/plain');
							if (plainText) {
								if (largeTextAsFile && plainText.length > PASTED_TEXT_CHARACTER_LIMIT) {
									// Delegate handling of large text pastes to the parent component.
									eventDispatch('paste', { event });
									event.preventDefault();
									return true;
								}

								// Workaround for mobile WebViews that strip line breaks when pasting from
								// clipboard suggestions (e.g., Gboard clipboard history).
								const isMobile = /Android|iPhone|iPad|iPod|Windows Phone/i.test(
									navigator.userAgent
								);
								const isWebView =
									typeof window !== 'undefined' &&
									(/wv/i.test(navigator.userAgent) || // Standard Android WebView flag
										(navigator.userAgent.includes('Android') &&
											!navigator.userAgent.includes('Chrome')) || // Other generic Android WebViews
										(navigator.userAgent.includes('Safari') &&
											!navigator.userAgent.includes('Version'))); // iOS WebView (in-app browsers)

								if (isMobile && isWebView && plainText.includes('\n')) {
									// Manually deconstruct the pasted text and insert it with hard breaks
									// to preserve the multi-line formatting.
									const { state, dispatch } = view;
									const { from, to } = state.selection;

									const lines = plainText.split('\n');
									const nodes = [];

									lines.forEach((line, index) => {
										if (index > 0) {
											nodes.push(state.schema.nodes.hardBreak.create());
										}
										if (line.length > 0) {
											nodes.push(state.schema.text(line));
										}
									});

									const fragment = Fragment.fromArray(nodes);
									const tr = state.tr.replaceWith(from, to, fragment);
									// 不自动滚动，避免干扰用户滚动位置
									dispatch(tr);
									event.preventDefault();
									return true;
								}
								// Let ProseMirror handle normal text paste in non-problematic environments.
								return false;
							}

							// Delegate image paste handling to the parent component.
							const hasImageFile = Array.from(event.clipboardData.files).some((file) =>
								file.type.startsWith('image/')
							);
							// Fallback for cases where an image is in dataTransfer.items but not clipboardData.files.
							const hasImageItem = Array.from(event.clipboardData.items).some((item) =>
								item.type.startsWith('image/')
							);

							const hasFile = Array.from(event.clipboardData.files).length > 0;

							if (hasImageFile || hasImageItem || hasFile) {
								// 检查是否在表格单元格内
								const { state } = view;
								const { $head } = state.selection;
								
								// 检查当前节点或父节点是否是表格相关节点
								let currentNode = $head;
								let isInTable = false;
								
								while (currentNode) {
									const nodeType = currentNode.parent.type.name;
									if (nodeType === 'table' || nodeType === 'tableRow' || nodeType === 'tableCell' || nodeType === 'tableHeader') {
										isInTable = true;
										break;
									}
									if (!currentNode.depth) break;
									currentNode = state.doc.resolve(currentNode.before());
								}
								
								// 如果配置了 fileHandler 和 onFilePaste，直接处理粘贴（确保在所有情况下都能工作）
								if (fileHandler && onFilePaste) {
									// 首先尝试从 files 中获取图片
									let files = Array.from(event.clipboardData.files);
									
									// 如果 files 中没有图片，尝试从 items 中提取图片
									if (files.length === 0 || !files.some(f => f.type.startsWith('image/'))) {
										const items = Array.from(event.clipboardData.items);
										const imageItems = items.filter(item => item.type.startsWith('image/'));
										
										// 将 items 中的图片转换为 File 对象
										for (const item of imageItems) {
											const file = item.getAsFile();
											if (file) {
												files.push(file);
											}
										}
									}
									
									if (files.length > 0 && files.some(f => f.type.startsWith('image/'))) {
										const htmlContent = event.clipboardData.getData('text/html');
										// 直接调用 onFilePaste，它会在内部处理图片保存和插入
										try {
											const result = onFilePaste(editor, files, htmlContent);
											// 如果返回 Promise，等待结果
											if (result && typeof result === 'object' && 'then' in result) {
												(result as Promise<boolean>).then((handled: boolean) => {
													if (handled) {
														event.preventDefault();
													}
												}).catch((error: any) => {
													console.error('粘贴图片失败:', error);
												});
												// 对于异步处理，先阻止默认行为，让onFilePaste处理
												event.preventDefault();
												return true;
											} else if (result === true) {
												// 如果同步返回 true，表示已处理
												event.preventDefault();
												return true;
											}
											// 如果返回 false，继续使用默认处理
										} catch (error) {
											console.error('粘贴图片失败:', error);
										}
									}
								}
								
								// 如果 onFilePaste 没有处理或返回 false，使用默认的事件分发
								eventDispatch('paste', { event });
								event.preventDefault();
								return true;
							}
						}
						// For all other cases, let ProseMirror perform its default paste behavior.
						// 不自动滚动，避免干扰用户滚动
						return false;
					}
				}
			},
			onBeforeCreate: ({ editor }) => {
				if (files) {
					editor.storage.files = files;
				}
			},
			onSelectionUpdate: onSelectionUpdate,
			enableInputRules: richText,
			enablePasteRules: richText
		});

		provider?.setEditor(editor, () => ({ md: mdValue, html: htmlValue, json: jsonValue }));

		if (messageInput) {
			selectTemplate();
		}
	});

	onDestroy(() => {
		if (provider) {
			provider.destroy();
		}

		if (editor) {
			editor.destroy();
		}
	});

	// 防止在用户编辑时触发 onValueChange（避免光标跳转）
	let lastEditorContent = '';
	let isInternalUpdate = false; // 标记是否是编辑器内部更新导致的 value 变化
	
	$: if (value !== null && editor && !collaboration) {
		// 如果是编辑器内部更新导致的 value 变化，不触发同步
		if (isInternalUpdate) {
			isInternalUpdate = false;
			lastEditorContent = value;
		} else {
			// 检查是否是用户正在编辑
			const currentHtml = editor.getHTML();
			const currentMd = turndownService.turndown(currentHtml).replace(/\u00a0/g, ' ');
			
			// 如果编辑器内容与传入的 value 相同，说明是用户编辑导致的更新，不需要同步
			if (value === currentMd || value === currentHtml || value === lastEditorContent) {
				// 用户编辑导致的更新，更新 lastEditorContent 但不触发同步
				lastEditorContent = value;
			} else {
				// 否则是外部更新，需要同步
				lastEditorContent = value;
				onValueChange();
			}
		}
	}

	const onValueChange = () => {
		if (!editor) return;

		// 保存当前光标位置（只在非 messageInput 模式下）
		const currentSelection = !messageInput ? editor.state.selection : null;
		const currentPos = currentSelection ? currentSelection.anchor : null;

		const jsonValue = editor.getJSON();
		const htmlValue = editor.getHTML();
		let mdValue = turndownService
			.turndown(
				(preserveBreaks ? htmlValue.replace(/<p><\/p>/g, '<br/>') : htmlValue).replace(
					/ {2,}/g,
					(m) => m.replace(/ /g, '\u00a0')
				)
			)
			.replace(/\u00a0/g, ' ');

		if (value === '') {
			editor.commands.clearContent(); // Clear content if value is empty
			selectTemplate();
			return;
		}

		let contentChanged = false;
		if (json) {
			if (JSON.stringify(value) !== JSON.stringify(jsonValue)) {
				editor.commands.setContent(value);
				contentChanged = true;
			}
		} else {
			if (raw) {
				if (value !== htmlValue) {
					editor.commands.setContent(value);
					contentChanged = true;
				}
			} else {
				if (value !== mdValue) {
					editor.commands.setContent(
						preserveBreaks
							? value
							: marked.parse(value.replaceAll(`\n<br/>`, `<br/>`), {
									breaks: false
								})
					);
					contentChanged = true;
				}
			}
		}

		// 如果内容改变了，根据模式处理光标位置
		if (contentChanged) {
			if (messageInput) {
				// messageInput 模式下执行模板选择
				selectTemplate();
			} else if (currentPos !== null && currentPos > 0) {
				// 非 messageInput 模式下，立即恢复光标位置（不使用 setTimeout）
				try {
					const docSize = editor.state.doc.content.size;
					// 确保位置在文档范围内
					const safePos = Math.min(currentPos, Math.max(1, docSize - 1));
					const $pos = editor.state.doc.resolve(safePos);
					// 使用 TextSelection.near 来创建选择
					const selection = TextSelection.near($pos);
					editor.view.dispatch(editor.state.tr.setSelection(selection));
				} catch (e) {
					// 如果恢复失败，保持默认行为（光标在开头）
					console.warn('无法恢复光标位置:', e);
				}
			} else {
				// 如果没有保存的位置，将光标放在开头（而不是末尾）
				try {
					const $pos = editor.state.doc.resolve(1);
					const selection = TextSelection.near($pos);
					editor.view.dispatch(editor.state.tr.setSelection(selection));
				} catch (e) {
					console.warn('无法设置光标位置:', e);
				}
			}
		}
	};
</script>

{#if richText && showFormattingToolbar && !fixedToolbar}
	<div bind:this={bubbleMenuElement} id="bubble-menu" class="p-0 {editor ? '' : 'hidden'}" style="max-width: min(calc(100vw - 2rem), 100%); box-sizing: border-box;">
		<FormattingButtons {editor} />
	</div>

	<div bind:this={floatingMenuElement} id="floating-menu" class="p-0 {editor ? '' : 'hidden'}" style="max-width: min(calc(100vw - 2rem), 100%); box-sizing: border-box;">
		<FormattingButtons {editor} />
	</div>
{/if}

<div
	class="relative w-full min-w-full {fixedToolbar ? 'flex flex-col' : ''} {className} {!editable
		? 'cursor-not-allowed'
		: ''}"
>
	{#if richText && showFormattingToolbar && fixedToolbar && toolbarPosition === 'top'}
		<!-- 固定工具栏（顶部） -->
		<div class="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-2">
			<FormattingButtons {editor} />
		</div>
	{/if}
	
	<div
		bind:this={element}
		class="relative w-full min-w-full {fixedToolbar ? 'flex-1 min-h-0 overflow-auto' : 'h-full min-h-fit'}"
		on:click={() => {
			// 点击其他地方时关闭右键菜单
			if (tableContextMenuVisible) {
				tableContextMenuVisible = false;
			}
		}}
		on:contextmenu|self={() => {
			// 在编辑器外部右键时关闭菜单
			tableContextMenuVisible = false;
		}}
	/>
	
	{#if richText && showFormattingToolbar && fixedToolbar && toolbarPosition === 'bottom'}
		<!-- 固定工具栏（底部） -->
		<div class="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-2">
			<FormattingButtons {editor} />
		</div>
	{/if}
</div>

<!-- 表格右键菜单 -->
<TableContextMenu
	{editor}
	x={tableContextMenuX}
	y={tableContextMenuY}
	visible={tableContextMenuVisible}
	on:close={() => {
		tableContextMenuVisible = false;
	}}
/>

<style>
	/* 表格基础样式 - 完全禁用滚动和拖动 */
	:global(.ProseMirror table) {
		border-collapse: collapse;
		width: 100%;
		max-width: 100%;
		margin: 1em 0;
		position: relative;
		/* 完全禁用表格滚动和拖动 */
		overflow: visible !important;
		touch-action: none !important;
		-webkit-user-select: none;
		user-select: none;
		/* 阻止表格的滚动和拖动行为 */
		pointer-events: auto;
		overscroll-behavior: none !important;
		-webkit-overflow-scrolling: auto !important;
		scroll-behavior: auto !important;
		/* 表格整体边框 */
		border: 2px solid #e5e7eb;
		border-radius: 6px;
		/* 减少transition以提高性能 */
		transition: border-color 0.15s ease, box-shadow 0.15s ease;
		/* 防止表格内容溢出和滚动 */
		display: table;
		table-layout: fixed;
		word-break: break-word;
		white-space: normal;
		/* 优化渲染性能 */
		will-change: auto;
		contain: layout style;
	}
	
	/* 表格行 - 禁用滚动 */
	:global(.ProseMirror table tr) {
		overflow: visible !important;
		touch-action: none !important;
		-webkit-user-select: none;
		user-select: none;
	}
	
	:global(.dark .ProseMirror table) {
		border-color: #4b5563;
	}
	
	/* 表格选中/聚焦时的整体高亮 */
	:global(.ProseMirror table:focus-within),
	:global(.ProseMirror table.has-focus) {
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}
	
	:global(.dark .ProseMirror table:focus-within),
	:global(.dark .ProseMirror table.has-focus) {
		border-color: #60a5fa;
		box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.15);
	}
	
	/* 表格单元格基础样式 - 允许文本选择但禁用滚动拖动 */
	:global(.ProseMirror table td),
	:global(.ProseMirror table th) {
		border: 1px solid #e5e7eb;
		padding: 0.75em;
		position: relative;
		/* 减少transition以提高性能 */
		transition: border-color 0.15s ease, background-color 0.15s ease;
		/* 允许单元格内的文本选择 */
		-webkit-user-select: text;
		user-select: text;
		min-width: 70px;
		/* 完全禁用单元格的滚动和拖动 */
		overflow: visible !important;
		touch-action: manipulation !important;
		overscroll-behavior: none !important;
		/* 防止单元格内容滚动 */
		display: table-cell;
		vertical-align: top;
		/* 禁用单元格的拖动行为 */
		draggable: false;
		/* 优化渲染性能 */
		will-change: auto;
		/* 确保文本大小写正常显示和输入 */
		text-transform: none !important;
		word-break: break-word;
		white-space: normal;
	}

	:global(.ProseMirror img) {
		max-width: 25%;
		height: auto;
		display: block;
		margin: 0.5rem 0;
	}
	
	/* 单元格内的内容 - 禁用滚动 */
	:global(.ProseMirror table td > *),
	:global(.ProseMirror table th > *) {
		overflow: visible !important;
		touch-action: manipulation !important;
		overscroll-behavior: none !important;
		/* 确保单元格内所有内容的大小写正常 */
		text-transform: none !important;
	}
	
	:global(.dark .ProseMirror table td),
	:global(.dark .ProseMirror table th) {
		border-color: #4b5563;
	}
	
	/* 表格单元格hover效果 */
	:global(.ProseMirror table td:hover),
	:global(.ProseMirror table th:hover) {
		background-color: #f9fafb;
		cursor: text;
	}
	
	:global(.dark .ProseMirror table td:hover),
	:global(.dark .ProseMirror table th:hover) {
		background-color: #374151;
	}
	
	/* 表格单元格选中状态 - 增强版 */
	:global(.ProseMirror table td[data-selected-cell]),
	:global(.ProseMirror table th[data-selected-cell]),
	:global(.ProseMirror table td.selectedCell),
	:global(.ProseMirror table th.selectedCell),
	:global(.ProseMirror table td:focus),
	:global(.ProseMirror table th:focus) {
		background-color: #dbeafe !important;
		box-shadow: inset 0 0 0 2px #3b82f6;
		border-color: #3b82f6 !important;
		outline: none;
	}
	
	:global(.dark .ProseMirror table td[data-selected-cell]),
	:global(.dark .ProseMirror table th[data-selected-cell]),
	:global(.dark .ProseMirror table td.selectedCell),
	:global(.dark .ProseMirror table th.selectedCell),
	:global(.dark .ProseMirror table td:focus),
	:global(.dark .ProseMirror table th:focus) {
		background-color: #1e3a5f !important;
		box-shadow: inset 0 0 0 2px #60a5fa;
		border-color: #60a5fa !important;
	}
	
	/* 表格行选中状态 */
	:global(.ProseMirror table tr.selectedRow) {
		background-color: #eff6ff;
	}
	
	:global(.dark .ProseMirror table tr.selectedRow) {
		background-color: #1e3a5f;
	}
	
	/* 表格整体选中状态 */
	:global(.ProseMirror table.selectedTable) {
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
	}
	
	:global(.dark .ProseMirror table.selectedTable) {
		border-color: #60a5fa;
		box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.25);
	}
	
	/* 表格选中时的整体高亮 */
	:global(.ProseMirror table.selectedTable) {
		outline: 2px solid #3b82f6;
		outline-offset: 2px;
		border-radius: 4px;
		transition: outline 0.2s ease;
	}
	
	:global(.dark .ProseMirror table.selectedTable) {
		outline-color: #60a5fa;
	}
	
	/* 表格单元格悬停效果 */
	:global(.ProseMirror table td:hover),
	:global(.ProseMirror table th:hover) {
		background-color: #f3f4f6;
		cursor: cell;
	}
	
	:global(.dark .ProseMirror table td:hover),
	:global(.dark .ProseMirror table th:hover) {
		background-color: #374151;
	}
	
	/* 表格单元格聚焦状态 */
	:global(.ProseMirror table td:focus),
	:global(.ProseMirror table th:focus) {
		outline: 2px solid #3b82f6;
		outline-offset: -2px;
	}
	
	:global(.dark .ProseMirror table td:focus),
	:global(.dark .ProseMirror table th:focus) {
		outline-color: #60a5fa;
	}
	
	/* 工具栏溢出控制 - 确保工具栏不会超出视口 */
	:global(#bubble-menu),
	:global(#floating-menu) {
		max-width: min(calc(100vw - 2rem), 100%) !important;
		overflow: visible !important;
		position: relative !important;
		box-sizing: border-box !important;
	}
	
	:global(#bubble-menu > *),
	:global(#floating-menu > *) {
		max-width: 100% !important;
		overflow-x: auto !important;
		overflow-y: visible !important;
		box-sizing: border-box !important;
	}
	
	/* Tippy 工具栏容器样式 - 强制限制宽度 */
	:global(.tippy-box[data-theme~='transparent']) {
		max-width: min(calc(100vw - 2rem), 100%) !important;
		width: auto !important;
		left: auto !important;
		right: auto !important;
		box-sizing: border-box !important;
	}
	
	:global(.tippy-box[data-theme~='transparent'] > .tippy-content) {
		max-width: 100% !important;
		width: 100% !important;
		overflow-x: auto !important;
		overflow-y: visible !important;
		padding: 0 !important;
		box-sizing: border-box !important;
	}
	
	/* 确保所有 Tippy 工具栏在视口内 */
	:global(.tippy-box) {
		max-width: min(calc(100vw - 2rem), 100%) !important;
		box-sizing: border-box !important;
	}
	
	:global(.tippy-content) {
		max-width: 100% !important;
		overflow-x: auto !important;
		overflow-y: visible !important;
		box-sizing: border-box !important;
	}
</style>
