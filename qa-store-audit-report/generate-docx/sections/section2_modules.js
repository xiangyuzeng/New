/**
 * Section 2: 12模块风险分析 (Module Risk Analysis).
 */

const { Paragraph, TextRun } = require('docx');
const { COLORS, FONTS, FONT_SIZES, severityColor } = require('../styles');
const { statusShading } = require('../styles');
const {
  buildTable,
  heading1,
  heading2,
  heading3,
  bodyText,
  bulletPoint,
  spacer,
  multiRunParagraph,
} = require('../utils');

function buildSection2(layer2, metadata) {
  const children = [];

  children.push(heading1('二、12模块风险分析'));

  // Overview
  children.push(heading2('2.1 模块排名概览'));

  children.push(bodyText(
    `本月共发现 ${layer2.total_issues} 个问题项，分布在 ${layer2.modules.length} 个模块中。`
  ));

  if (layer2.critical_modules.length > 0) {
    children.push(bodyText(
      `⚠ 含关键项（S项）的模块：${layer2.critical_modules.join('、')}`,
      { color: COLORS.RED, bold: true }
    ));
  }
  if (layer2.systemic_modules.length > 0) {
    children.push(bodyText(
      `⚠ 系统性问题模块（影响>50%门店）：${layer2.systemic_modules.join('、')}`,
      { color: COLORS.WARNING, bold: true }
    ));
  }

  children.push(spacer(100));

  // Module ranking table
  const headers = [
    '排名', '模块', '问题数', '影响门店', '占比', '扣分合计',
    'S项', 'M项', 'G项', 'L项',
  ];

  const rows = layer2.modules.map(mod => [
    String(mod.rank),
    mod.module_name,
    String(mod.issue_count),
    String(mod.affected_store_count),
    `${mod.affected_store_pct}%`,
    String(mod.total_deductions),
    String(mod.severity_breakdown.S || 0),
    String(mod.severity_breakdown.M || 0),
    String(mod.severity_breakdown.G || 0),
    String(mod.severity_breakdown.L || 0),
  ]);

  children.push(
    buildTable(headers, rows, {
      colWidths: [6, 14, 8, 9, 8, 10, 8, 8, 8, 8],
      cellFormatter: (value, rowIdx, colIdx) => {
        const mod = layer2.modules[rowIdx];
        if (!mod) return {};

        // Highlight critical modules
        if (colIdx === 1 && mod.has_critical) {
          return {
            color: COLORS.RED,
            bold: true,
            shading: statusShading('critical'),
          };
        }
        if (colIdx === 1 && mod.is_systemic) {
          return {
            color: COLORS.WARNING,
            bold: true,
            shading: statusShading('warning'),
          };
        }
        // S column
        if (colIdx === 6 && parseInt(value) > 0) {
          return { color: COLORS.RED, bold: true };
        }
        // M column
        if (colIdx === 7 && parseInt(value) > 0) {
          return { color: COLORS.WARNING, bold: true };
        }
        return {};
      },
    })
  );

  children.push(spacer(200));

  // Top 3 modules detail
  children.push(heading2('2.2 重点模块分析'));

  const top3 = layer2.modules.slice(0, 3);
  top3.forEach((mod, idx) => {
    children.push(heading3(
      `${idx + 1}. ${mod.module_name}（${mod.module_name_en}）— ${mod.issue_count} 个问题`
    ));

    // Severity summary
    const sevParts = [];
    if (mod.severity_breakdown.S) sevParts.push(`S项 ${mod.severity_breakdown.S} 个`);
    if (mod.severity_breakdown.M) sevParts.push(`M项 ${mod.severity_breakdown.M} 个`);
    if (mod.severity_breakdown.G) sevParts.push(`G项 ${mod.severity_breakdown.G} 个`);
    if (mod.severity_breakdown.L) sevParts.push(`L项 ${mod.severity_breakdown.L} 个`);

    children.push(bulletPoint(
      `严重级别分布：${sevParts.join('，') || '无'}`
    ));
    children.push(bulletPoint(
      `影响门店：${mod.affected_store_count} 家（${mod.affected_store_pct}%），扣分合计：${mod.total_deductions}`
    ));

    // Top issues
    if (mod.top_issues && mod.top_issues.length > 0) {
      children.push(bulletPoint('主要问题：'));
      mod.top_issues.forEach(issue => {
        const storeList = issue.stores.length > 0
          ? `（涉及: ${issue.stores.slice(0, 3).join(', ')}${issue.stores.length > 3 ? '等' : ''}）`
          : '';
        children.push(bodyText(
          `    - ${issue.description} × ${issue.count} 次${storeList}`,
          { color: COLORS.TEXT_DARK }
        ));
      });
    }

    children.push(spacer(100));
  });

  // Unmapped labels warning
  if (layer2.unmapped_labels && layer2.unmapped_labels.length > 0) {
    children.push(spacer(100));
    children.push(heading2('2.3 未映射标签'));
    children.push(bodyText(
      `以下标签未映射到12模块分类中，已归入"其他"类别。建议核实并更新映射配置：`,
      { italics: true }
    ));
    layer2.unmapped_labels.forEach(label => {
      children.push(bulletPoint(label));
    });
  }

  children.push(spacer(200));

  return {
    properties: {
      page: {
        margin: { top: 1440, right: 1080, bottom: 1440, left: 1080 },
      },
    },
    children,
  };
}

module.exports = { buildSection2 };
