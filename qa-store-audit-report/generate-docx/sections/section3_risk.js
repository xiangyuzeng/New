/**
 * Section 3: 风险等级分布 (Risk Level Distribution).
 */

const { Paragraph, TextRun } = require('docx');
const { COLORS, FONTS, FONT_SIZES, severityColor } = require('../styles');
const { statusShading } = require('../styles');
const {
  buildTable,
  heading1,
  heading2,
  bodyText,
  bulletPoint,
  spacer,
  multiRunParagraph,
} = require('../utils');

function buildSection3(layer3, metadata) {
  const children = [];

  children.push(heading1('三、风险等级分布'));

  // Overview
  children.push(heading2('3.1 整体分布'));

  children.push(bodyText(
    `本月共发现 ${layer3.total_issues} 个问题项，按严重程度分布如下：`
  ));

  // Distribution table
  const dist = layer3.severity_distribution;
  const pct = layer3.severity_percentages;

  const distRows = [
    ['S项（关键项）', String(dist.S || 0), `${pct.S || 0}%`, '立即整改，2天内闭环'],
    ['M项（重要项）', String(dist.M || 0), `${pct.M || 0}%`, '优先整改，7天内闭环'],
    ['G项（一般项）', String(dist.G || 0), `${pct.G || 0}%`, '常规整改，14天内闭环'],
    ['L项（轻微项）', String(dist.L || 0), `${pct.L || 0}%`, '提醒改善，14天内闭环'],
  ];
  if (dist.O > 0) {
    distRows.push(['其他', String(dist.O), `${pct.O || 0}%`, '-']);
  }

  children.push(
    buildTable(
      ['风险等级', '数量', '占比', 'SLA要求'],
      distRows,
      {
        colWidths: [25, 15, 15, 45],
        cellFormatter: (value, rowIdx, colIdx) => {
          if (colIdx === 0) {
            const colors = [COLORS.RED, COLORS.WARNING, COLORS.BLUE_ACCENT, COLORS.TEXT_DARK, COLORS.BORDER_GRAY];
            return { color: colors[rowIdx] || COLORS.TEXT_DARK, bold: true };
          }
          if (colIdx === 1 && rowIdx === 0 && parseInt(value) > 0) {
            return {
              color: COLORS.RED,
              bold: true,
              shading: statusShading('critical'),
            };
          }
          return {};
        },
      }
    )
  );

  children.push(spacer(200));

  // S-items detail
  children.push(heading2('3.2 S项（关键项）详情'));

  if (layer3.s_items_count === 0) {
    children.push(bodyText(
      '本月未发现S项（关键项），食品安全关键控制点表现良好。',
      { color: COLORS.GREEN, bold: true }
    ));
  } else {
    children.push(bodyText(
      `本月共发现 ${layer3.s_items_count} 个S项（关键项），必须立即整改：`,
      { color: COLORS.RED, bold: true }
    ));

    const sHeaders = ['#', '门店', '模块', '检查项目', '问题描述', '扣分', '日期'];
    const sRows = layer3.s_items_detail.map((item, idx) => [
      String(idx + 1),
      item.store_name,
      item.module,
      (item.check_item || '').substring(0, 60),
      (item.description || '').substring(0, 80),
      String(item.deduction),
      (item.check_date || '').substring(0, 10),
    ]);

    children.push(
      buildTable(sHeaders, sRows, {
        colWidths: [5, 12, 10, 22, 25, 8, 12],
        cellFormatter: (value, rowIdx, colIdx) => {
          // Red highlight for entire S-item rows
          return { shading: statusShading('critical') };
        },
      })
    );
  }

  children.push(spacer(200));

  // M-items top modules
  children.push(heading2('3.3 M项（重要项）分布'));

  const mModules = layer3.m_top_modules;
  if (Object.keys(mModules).length === 0) {
    children.push(bodyText('本月未发现M项。'));
  } else {
    children.push(bodyText(`M项共 ${dist.M || 0} 个，主要集中在以下模块：`));
    const mRows = Object.entries(mModules).map(([mod, count]) => [mod, String(count)]);
    children.push(
      buildTable(['模块', '数量'], mRows, { colWidths: [70, 30] })
    );
  }

  children.push(spacer(100));

  // G/L items summary
  children.push(heading2('3.4 G项/L项分布'));

  const gModules = layer3.g_top_modules;
  const lModules = layer3.l_top_modules;

  if (Object.keys(gModules).length > 0) {
    children.push(bodyText(`G项（一般项）共 ${dist.G || 0} 个，主要模块：`));
    Object.entries(gModules).forEach(([mod, count]) => {
      children.push(bulletPoint(`${mod}：${count} 个`));
    });
  }

  if (Object.keys(lModules).length > 0) {
    children.push(bodyText(`L项（轻微项）共 ${dist.L || 0} 个，主要模块：`));
    Object.entries(lModules).forEach(([mod, count]) => {
      children.push(bulletPoint(`${mod}：${count} 个`));
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

module.exports = { buildSection3 };
