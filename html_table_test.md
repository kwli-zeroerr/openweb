# HTML 表格测试

## 测试 1: 简单 HTML 表格

<table border="1" style="border-collapse: collapse; width: 100%;">
<thead>
<tr>
<th>关节型号</th>
<th>谐波减速机型号-速比</th>
<th>启停峰值扭矩(Nm)</th>
<th>平均负载转矩容许最大值(Nm)</th>
<th>额定扭矩(Nm)</th>
</tr>
</thead>
<tbody>
<tr>
<td>eRob70F</td>
<td>14-50 Ultra-flat</td>
<td>12</td>
<td>4.8</td>
<td>3.7</td>
</tr>
<tr>
<td>eRob70H</td>
<td>14-80 Ultra-flat</td>
<td>16</td>
<td>7.7</td>
<td>5.4</td>
</tr>
<tr>
<td>eRob80H</td>
<td>14-100 Ultra-flat</td>
<td>19</td>
<td>7.7</td>
<td>5.4</td>
</tr>
</tbody>
</table>

## 测试 2: 带样式的 HTML 表格

<div style="overflow-x: auto;">
<table border="1" style="border-collapse: collapse; width: 100%; background-color: #f9f9f9;">
<thead>
<tr style="background-color: #e0e0e0;">
<th style="padding: 8px; border: 1px solid #ccc;">参数类型</th>
<th style="padding: 8px; border: 1px solid #ccc;">eRob70F</th>
<th style="padding: 8px; border: 1px solid #ccc;">eRob70H</th>
<th style="padding: 8px; border: 1px solid #ccc;">eRob80H</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 8px; border: 1px solid #ccc;">启停峰值扭矩</td>
<td style="padding: 8px; border: 1px solid #ccc;">12</td>
<td style="padding: 8px; border: 1px solid #ccc;">16</td>
<td style="padding: 8px; border: 1px solid #ccc;">19</td>
</tr>
<tr>
<td style="padding: 8px; border: 1px solid #ccc;">平均负载转矩容许最大值</td>
<td style="padding: 8px; border: 1px solid #ccc;">4.8</td>
<td style="padding: 8px; border: 1px solid #ccc;">7.7</td>
<td style="padding: 8px; border: 1px solid #ccc;">7.7</td>
</tr>
<tr>
<td style="padding: 8px; border: 1px solid #ccc;">额定扭矩</td>
<td style="padding: 8px; border: 1px solid #ccc;">3.7</td>
<td style="padding: 8px; border: 1px solid #ccc;">5.4</td>
<td style="padding: 8px; border: 1px solid #ccc;">5.4</td>
</tr>
</tbody>
</table>
</div>

## 测试 3: 复杂 HTML 表格（合并单元格）

<table border="1" style="border-collapse: collapse; width: 100%;">
<thead>
<tr>
<th rowspan="2">关节型号</th>
<th colspan="3">谐波减速机型号-速比</th>
<th rowspan="2">启停峰值扭矩(Nm)</th>
<th rowspan="2">平均负载转矩容许最大值(Nm)</th>
</tr>
<tr>
<th>eRob70F</th>
<th>eRob70H</th>
<th>eRob80H</th>
</tr>
</thead>
<tbody>
<tr>
<td>14-50 Ultra-flat</td>
<td>12</td>
<td>4.8</td>
<td>3.7</td>
<td>23</td>
<td>60</td>
</tr>
<tr>
<td>14-80 Ultra-flat</td>
<td>16</td>
<td>7.7</td>
<td>5.4</td>
<td>35</td>
<td>37.5</td>
</tr>
<tr>
<td>14-100 Ultra-flat</td>
<td>19</td>
<td>7.7</td>
<td>5.4</td>
<td>35</td>
<td>30</td>
</tr>
</tbody>
</table>

## 测试 4: 普通 Markdown 表格对比

| 参数类型 | eRob70F | eRob70H | eRob80H |
|---------|---------|---------|---------|
| 启停峰值扭矩 | 12 | 16 | 19 |
| 平均负载转矩容许最大值 | 4.8 | 7.7 | 7.7 |
| 额定扭矩 | 3.7 | 5.4 | 5.4 |
