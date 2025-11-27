# HTML 表格功能测试

## 测试说明
现在 Open WebUI 已经支持 HTML 表格渲染！你可以在对话中直接使用 HTML 代码来创建复杂的表格。

## 测试用例

### 1. 简单表格
```html
<table border="1" style="border-collapse: collapse; width: 100%;">
<tr>
<th>参数</th>
<th>值</th>
</tr>
<tr>
<td>扭矩</td>
<td>12 Nm</td>
</tr>
</table>
```

### 2. 复杂表格（合并单元格）
```html
<table border="1" style="border-collapse: collapse; width: 100%;">
<thead>
<tr>
<th rowspan="2">型号</th>
<th colspan="2">参数</th>
</tr>
<tr>
<th>扭矩</th>
<th>转速</th>
</tr>
</thead>
<tbody>
<tr>
<td>eRob70F</td>
<td>12 Nm</td>
<td>60 RPM</td>
</tr>
</tbody>
</table>
```

### 3. 带样式的表格
```html
<div style="overflow-x: auto;">
<table border="1" style="border-collapse: collapse; width: 100%; background-color: #f9f9f9;">
<thead>
<tr style="background-color: #e0e0e0;">
<th style="padding: 8px;">参数</th>
<th style="padding: 8px;">值</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 8px;">扭矩</td>
<td style="padding: 8px;">12 Nm</td>
</tr>
</tbody>
</table>
</div>
```

## 使用方法
1. 在 Open WebUI 的对话中输入上述 HTML 代码
2. 系统会自动渲染为表格
3. 支持响应式设计和自定义样式

## 注意事项
- HTML 内容会经过 DOMPurify 安全清理
- 支持大部分 HTML 表格标签和属性
- 建议使用内联样式以确保样式正确应用
