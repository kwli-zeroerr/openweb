/**
 * 连接线服务层
 * 处理连接线的绘制、编辑逻辑
 */

import type { WorkflowNode, WorkflowConnection, ConnectionSide } from "../types";

/**
 * 获取节点的连接点坐标
 */
export function getConnectionPoint(
  node: WorkflowNode,
  side: ConnectionSide
): { x: number; y: number } {
  switch (side) {
    case "top":
      return { x: node.x + node.width / 2, y: node.y };
    case "bottom":
      return { x: node.x + node.width / 2, y: node.y + node.height };
    case "left":
      return { x: node.x, y: node.y + node.height / 2 };
    case "right":
      return { x: node.x + node.width, y: node.y + node.height / 2 };
  }
}

/**
 * 计算直角折线路径（始终使用水平和垂直线段）
 */
export function calculatePolylinePath(
  fromNode: WorkflowNode,
  fromSide: ConnectionSide,
  toNode: WorkflowNode,
  toSide: ConnectionSide,
  controlPoints?: Array<{ x: number; y: number }>
): string {
  const fromPoint = getConnectionPoint(fromNode, fromSide);
  const toPoint = getConnectionPoint(toNode, toSide);
  
  // 如果有用户编辑的控制点，使用控制点生成直角折线
  if (controlPoints && controlPoints.length > 0) {
    let path = `M ${fromPoint.x} ${fromPoint.y}`;
    let lastX = fromPoint.x;
    let lastY = fromPoint.y;
    
    // 遍历控制点，生成直角路径
    for (let i = 0; i < controlPoints.length; i++) {
      const cp = controlPoints[i];
      // 优先水平移动，再垂直移动（保持直角）
      if (Math.abs(cp.x - lastX) > Math.abs(cp.y - lastY)) {
        // 先水平移动
        path += ` L ${cp.x} ${lastY}`;
        // 再垂直移动
        path += ` L ${cp.x} ${cp.y}`;
      } else {
        // 先垂直移动
        path += ` L ${lastX} ${cp.y}`;
        // 再水平移动
        path += ` L ${cp.x} ${cp.y}`;
      }
      lastX = cp.x;
      lastY = cp.y;
    }
    // 连接到终点（保持直角）
    if (Math.abs(toPoint.x - lastX) > Math.abs(toPoint.y - lastY)) {
      path += ` L ${toPoint.x} ${lastY} L ${toPoint.x} ${toPoint.y}`;
    } else {
      path += ` L ${lastX} ${toPoint.y} L ${toPoint.x} ${toPoint.y}`;
    }
    return path;
  }
  
  // 自动计算直角折线：根据方向生成标准L形或U形路径
  const midX = (fromPoint.x + toPoint.x) / 2;
  const midY = (fromPoint.y + toPoint.y) / 2;
  
  let path = `M ${fromPoint.x} ${fromPoint.y}`;
  
  // 根据连接方向生成标准直角路径（L形或U形）
  if (fromSide === "top" || fromSide === "bottom") {
    // 从上/下出发
    if (toSide === "top" || toSide === "bottom") {
      // 目标也是上/下：U形路径（垂直-水平-垂直）
      path += ` L ${fromPoint.x} ${midY} L ${toPoint.x} ${midY} L ${toPoint.x} ${toPoint.y}`;
    } else if (toSide === "left") {
      // 目标在左：L形路径（垂直-水平）
      path += ` L ${fromPoint.x} ${toPoint.y} L ${toPoint.x} ${toPoint.y}`;
    } else {
      // 目标在右：L形路径（垂直-水平）
      path += ` L ${fromPoint.x} ${toPoint.y} L ${toPoint.x} ${toPoint.y}`;
    }
  } else if (fromSide === "left") {
    // 从左边出发
    if (toSide === "left") {
      // 目标也在左：U形路径（水平-垂直-水平）
      path += ` L ${midX} ${fromPoint.y} L ${midX} ${toPoint.y} L ${toPoint.x} ${toPoint.y}`;
    } else if (toSide === "right") {
      // 目标在右：U形路径（水平-垂直-水平）
      path += ` L ${midX} ${fromPoint.y} L ${midX} ${toPoint.y} L ${toPoint.x} ${toPoint.y}`;
    } else if (toSide === "top") {
      // 目标在上：L形路径（水平-垂直）
      path += ` L ${toPoint.x} ${fromPoint.y} L ${toPoint.x} ${toPoint.y}`;
    } else {
      // 目标在下：L形路径（水平-垂直）
      path += ` L ${toPoint.x} ${fromPoint.y} L ${toPoint.x} ${toPoint.y}`;
    }
  } else {
    // 从右边出发
    if (toSide === "left") {
      // 目标在左：U形路径（水平-垂直-水平）
      path += ` L ${midX} ${fromPoint.y} L ${midX} ${toPoint.y} L ${toPoint.x} ${toPoint.y}`;
    } else if (toSide === "right") {
      // 目标也在右：U形路径（水平-垂直-水平）
      path += ` L ${midX} ${fromPoint.y} L ${midX} ${toPoint.y} L ${toPoint.x} ${toPoint.y}`;
    } else if (toSide === "top") {
      // 目标在上：L形路径（水平-垂直）
      path += ` L ${toPoint.x} ${fromPoint.y} L ${toPoint.x} ${toPoint.y}`;
    } else {
      // 目标在下：L形路径（水平-垂直）
      path += ` L ${toPoint.x} ${fromPoint.y} L ${toPoint.x} ${toPoint.y}`;
    }
  }
  
  return path;
}

/**
 * 添加控制点
 */
export function addControlPoint(
  connectionId: string,
  x: number,
  y: number,
  connections: WorkflowConnection[]
): WorkflowConnection[] {
  return connections.map(conn => {
    if (conn.id === connectionId) {
      const points = conn.controlPoints || [];
      return {
        ...conn,
        controlPoints: [...points, { x, y }]
      };
    }
    return conn;
  });
}

/**
 * 删除控制点
 */
export function deleteControlPoint(
  connectionId: string,
  pointIndex: number,
  connections: WorkflowConnection[]
): WorkflowConnection[] {
  return connections.map(conn => {
    if (conn.id === connectionId && conn.controlPoints) {
      const points = [...conn.controlPoints];
      points.splice(pointIndex, 1);
      return {
        ...conn,
        controlPoints: points
      };
    }
    return conn;
  });
}

/**
 * 更新控制点位置（添加直角约束：只能水平或垂直移动）
 */
export function updateControlPoint(
  connectionId: string,
  pointIndex: number,
  x: number,
  y: number,
  connections: WorkflowConnection[],
  fromPoint?: { x: number; y: number },
  toPoint?: { x: number; y: number }
): WorkflowConnection[] {
  return connections.map(conn => {
    if (conn.id === connectionId && conn.controlPoints) {
      const points = [...conn.controlPoints];
      const originalPoint = points[pointIndex];
      
      // 计算水平偏移和垂直偏移
      const deltaX = Math.abs(x - originalPoint.x);
      const deltaY = Math.abs(y - originalPoint.y);
      
      // 直角约束：根据拖动方向，只移动一个维度（水平或垂直）
      let constrainedPoint: { x: number; y: number };
      if (deltaX > deltaY) {
        // 水平拖动：只改变 x，保持 y 不变
        constrainedPoint = { x, y: originalPoint.y };
      } else {
        // 垂直拖动：只改变 y，保持 x 不变
        constrainedPoint = { x: originalPoint.x, y };
      }
      
      points[pointIndex] = constrainedPoint;
      return {
        ...conn,
        controlPoints: points
      };
    }
    return conn;
  });
}

