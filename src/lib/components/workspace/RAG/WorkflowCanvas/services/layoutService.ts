import type { WorkflowNode } from '../types';

export interface AlignOptions {
  snapToGrid: boolean;
  gridSize: number;
}

export function snap(value: number, opts: AlignOptions): number {
  if (!opts.snapToGrid) return value;
  return Math.round(value / opts.gridSize) * opts.gridSize;
}

export function alignNodes(
  nodes: WorkflowNode[],
  selectedNode: WorkflowNode | null,
  alignment: 'left' | 'right' | 'top' | 'bottom' | 'center' | 'middle',
  opts: AlignOptions
): WorkflowNode[] {
  if (!selectedNode) return nodes;
  if (alignment === 'left') {
    return nodes.map(n => n.id === selectedNode.id ? { ...n, x: 0 } : n);
  }
  if (alignment === 'right') {
    return nodes.map(n => n.id === selectedNode.id ? { ...n, x: snap(800 - n.width, opts) } : n);
  }
  if (alignment === 'top') {
    return nodes.map(n => n.id === selectedNode.id ? { ...n, y: 0 } : n);
  }
  if (alignment === 'bottom') {
    return nodes.map(n => n.id === selectedNode.id ? { ...n, y: snap(600 - n.height, opts) } : n);
  }
  if (alignment === 'center') {
    return nodes.map(n => n.id === selectedNode.id ? { ...n, x: snap(400 - n.width / 2, opts) } : n);
  }
  if (alignment === 'middle') {
    return nodes.map(n => n.id === selectedNode.id ? { ...n, y: snap(300 - n.height / 2, opts) } : n);
  }
  return nodes;
}

export function distributeNodes(
  nodes: WorkflowNode[],
  selectedNode: WorkflowNode | null,
  direction: 'horizontal' | 'vertical',
  opts: AlignOptions
): WorkflowNode[] {
  // 预留：当前单选时直接返回
  return nodes;
}


