/**
 * buildActionItemTree – Biến đổi flat array thành tree structure
 * ---
 * Sử dụng parent_id để xây dựng cấu trúc cây đệ quy.
 * Items không có parent_id (null) → node gốc (thường là Epic).
 * Items có parent_id → trở thành children của node cha.
 */

import type { ActionItem } from '../../types/supabase-models'

export interface ActionItemTreeNode {
  /** Dữ liệu gốc từ DB */
  item: ActionItem
  /** Các node con (tasks thuộc epic, subtasks thuộc task) */
  children: ActionItemTreeNode[]
  /** Depth level — 0 = root, 1 = child, 2 = grandchild */
  depth: number
}

/**
 * Chuyển flat ActionItem[] thành cây ActionItemTreeNode[].
 *
 * Thuật toán O(n):
 * 1. Tạo map id → node
 * 2. Duyệt qua từng item:
 *    - Nếu parent_id === null → push vào roots
 *    - Nếu parent_id trỏ tới node đã biết → push vào children của parent
 *    - Nếu parent_id trỏ tới node chưa biết → fallback push vào roots (orphan safety)
 *
 * @param items - Flat array từ Supabase
 * @returns Tree array (chỉ chứa root nodes, children đã nested bên trong)
 */
export function buildActionItemTree(items: ActionItem[]): ActionItemTreeNode[] {
  const nodeMap = new Map<string, ActionItemTreeNode>()
  const roots: ActionItemTreeNode[] = []

  // Pass 1: Tạo tất cả nodes
  for (const item of items) {
    nodeMap.set(item.id, { item, children: [], depth: 0 })
  }

  // Pass 2: Link parent → children
  for (const item of items) {
    const node = nodeMap.get(item.id)!

    if (item.parent_id && nodeMap.has(item.parent_id)) {
      const parent = nodeMap.get(item.parent_id)!
      node.depth = parent.depth + 1
      parent.children.push(node)
    } else {
      // Root node (parent_id === null) hoặc orphan (parent không tồn tại)
      roots.push(node)
    }
  }

  // Pass 3: Fix depth cho multi-level nesting (subtask → task → epic)
  function fixDepth(nodes: ActionItemTreeNode[], depth: number) {
    for (const n of nodes) {
      n.depth = depth
      if (n.children.length > 0) {
        fixDepth(n.children, depth + 1)
      }
    }
  }
  fixDepth(roots, 0)

  return roots
}

/**
 * Flatten tree thành flat list (giữ depth) — hữu ích cho tính toán summary.
 */
export function flattenTree(nodes: ActionItemTreeNode[]): ActionItemTreeNode[] {
  const result: ActionItemTreeNode[] = []
  function walk(list: ActionItemTreeNode[]) {
    for (const n of list) {
      result.push(n)
      walk(n.children)
    }
  }
  walk(nodes)
  return result
}
