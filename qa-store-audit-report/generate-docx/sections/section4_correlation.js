/**
 * Section 4: 模块与门店关联分析 (Module-Store Correlation Analysis).
 */

const { Paragraph, TextRun } = require('docx');
const { COLORS, FONTS, FONT_SIZES } = require('../styles');
const {
  buildTable,
  heading1,
  heading2,
  bodyText,
  bulletPoint,
  spacer,
} = require('../utils');

function buildSection4(layer2, layer1, metadata) {
  const children = [];

  children.push(heading1('四、模块与门店关联分析'));

  const conn = layer2.store_module_connection || {};

  // Lowest scoring store breakdown
  children.push(heading2('4.1 最低分门店问题归因'));

  if (layer1.lowest_store && layer1.lowest_store.name) {
    children.push(bodyText(
      `最低分门店 ${layer1.lowest_store.name}（${layer1.lowest_store.score} 分）的扣分来源：`
    ));

    const lowestModules = conn.lowest_store_modules || [];
    if (lowestModules.length > 0) {
      const rows = lowestModules.map(m => [m.module, String(m.deduction)]);
      children.push(
        buildTable(['模块', '扣分'], rows, { colWidths: [60, 40] })
      );
    } else {
      children.push(bodyText('暂无详细模块扣分数据。'));
    }
  } else {
    children.push(bodyText('暂无门店评分数据。'));
  }

  children.push(spacer(200));

  // Highest scoring store - clean modules
  children.push(heading2('4.2 最高分门店优势模块'));

  if (layer1.highest_store && layer1.highest_store.name) {
    children.push(bodyText(
      `最高分门店 ${layer1.highest_store.name}（${layer1.highest_store.score} 分）以下模块零扣分：`
    ));

    const cleanModules = conn.highest_store_modules || [];
    if (cleanModules.length > 0) {
      cleanModules.forEach(mod => {
        children.push(bulletPoint(`${mod} ✓`, { color: COLORS.GREEN }));
      });
    } else {
      children.push(bodyText('该门店所有模块均有扣分项。'));
    }
  }

  children.push(spacer(200));

  // Most improved store analysis
  children.push(heading2('4.3 进步门店分析'));

  if (layer1.most_improved) {
    children.push(bodyText(
      `进步最大门店 ${layer1.most_improved.name}（+${layer1.most_improved.change} 分），当月仍存在以下模块问题：`
    ));

    const improvedModules = conn.most_improved_modules || [];
    if (improvedModules.length > 0) {
      const rows = improvedModules.map(m => [
        m.module || '',
        String(m.deduction || 0),
      ]);
      children.push(
        buildTable(['模块', '扣分'], rows, { colWidths: [60, 40] })
      );
    } else {
      children.push(bodyText('该门店当月巡检无扣分项，表现优异。'));
    }
  } else {
    children.push(bodyText(
      '无上月对比数据，暂无法分析门店进步情况。待积累多月数据后可进行趋势分析。'
    ));
  }

  children.push(spacer(200));

  // Cross-module analysis: which modules affect the most stores
  children.push(heading2('4.4 模块覆盖面分析'));

  const modulesAffecting = layer2.modules
    .filter(m => m.affected_store_pct > 0)
    .sort((a, b) => b.affected_store_pct - a.affected_store_pct);

  if (modulesAffecting.length > 0) {
    children.push(bodyText('各模块影响门店覆盖率（按影响面从大到小）：'));

    const covRows = modulesAffecting.map(m => [
      m.module_name,
      String(m.affected_store_count),
      `${m.affected_store_pct}%`,
      m.is_systemic ? '⚠ 系统性' : '—',
    ]);

    children.push(
      buildTable(
        ['模块', '影响门店数', '覆盖率', '风险标记'],
        covRows,
        {
          colWidths: [30, 20, 20, 30],
          cellFormatter: (value, rowIdx, colIdx) => {
            if (colIdx === 3 && value.includes('系统性')) {
              return { color: COLORS.WARNING, bold: true };
            }
            return {};
          },
        }
      )
    );
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

module.exports = { buildSection4 };
