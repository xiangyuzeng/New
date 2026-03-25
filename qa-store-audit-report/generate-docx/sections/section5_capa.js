/**
 * Section 5: 整改归因与效率 (CAPA & Attribution — placeholder).
 */

const { Paragraph, TextRun } = require('docx');
const { COLORS, FONTS, FONT_SIZES } = require('../styles');
const { statusShading } = require('../styles');
const {
  buildTable,
  heading1,
  heading2,
  bodyText,
  bulletPoint,
  spacer,
} = require('../utils');

function buildSection5(layer4, metadata) {
  const children = [];

  children.push(heading1('五、整改归因与效率'));

  // Data availability notice
  children.push(heading2('5.1 数据现状说明'));

  children.push(bodyText(
    '当前QA系统数据导出中不包含以下整改跟踪字段，本章节为模板占位，待系统升级后完善：',
    { italics: true }
  ));

  layer4.missing_fields.forEach(field => {
    children.push(bulletPoint(field));
  });

  children.push(spacer(200));

  // SLA standards
  children.push(heading2('5.2 SLA整改时限标准'));

  const sla = layer4.template_structure.sla_standards;
  const slaRows = Object.values(sla).map(s => [
    s.label,
    s.deadline,
    `发现后 ${s.days} 天内完成整改并验证`,
  ]);

  children.push(
    buildTable(
      ['风险等级', '整改时限', '要求'],
      slaRows,
      { colWidths: [25, 20, 55] }
    )
  );

  children.push(spacer(200));

  // Recommended workflow
  children.push(heading2('5.3 建议整改闭环流程'));

  const workflow = layer4.template_structure.workflow;
  workflow.forEach(step => {
    children.push(bodyText(step));
  });

  children.push(spacer(200));

  // Keyword-based attribution (best effort)
  children.push(heading2('5.4 基于关键词的初步归因'));

  children.push(bodyText(
    layer4.disclaimer,
    { italics: true, color: COLORS.WARNING }
  ));

  children.push(spacer(100));

  const attr = layer4.keyword_attribution;
  if (attr.details && attr.details.length > 0) {
    children.push(bodyText(
      `共分析 ${attr.total_analyzed} 条问题描述，其中 ${attr.total_attributed} 条可归因（归因率 ${attr.attribution_rate}%）。`
    ));

    const attrRows = attr.details.map(d => [
      d.category,
      String(d.count),
      d.matched_keywords.slice(0, 5).join(', '),
    ]);

    children.push(
      buildTable(
        ['归因类别', '匹配数量', '匹配关键词'],
        attrRows,
        { colWidths: [20, 15, 65] }
      )
    );

    // Sample details
    children.push(spacer(100));
    attr.details.forEach(d => {
      if (d.samples && d.samples.length > 0) {
        children.push(bodyText(`${d.category} 归因示例：`, { bold: true }));
        d.samples.slice(0, 3).forEach(s => {
          children.push(bulletPoint(
            `${s.store_name} / ${s.module}：${s.description}`
          ));
        });
      }
    });
  } else {
    children.push(bodyText(
      '问题描述字段中未匹配到足够的归因关键词。建议在巡检系统中增加结构化的责任归属字段。'
    ));
  }

  children.push(spacer(200));

  // Template for future data
  children.push(heading2('5.5 待完善：整改效率跟踪模板'));

  children.push(bodyText(
    '以下为系统升级后可自动生成的整改效率分析表结构：'
  ));

  children.push(
    buildTable(
      ['风险等级', 'SLA达标数', '超期数', '达标率', '平均闭环天数'],
      [
        ['S项', '-', '-', '-', '-'],
        ['M项', '-', '-', '-', '-'],
        ['G项', '-', '-', '-', '-'],
        ['L项', '-', '-', '-', '-'],
      ],
      { colWidths: [20, 20, 15, 20, 25] }
    )
  );

  children.push(spacer(100));
  children.push(bodyText(
    '（以上数据待整改工单系统对接后自动填充）',
    { italics: true, color: COLORS.BORDER_GRAY }
  ));

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

module.exports = { buildSection5 };
