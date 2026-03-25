/**
 * Section 6: 建议与下一步行动 (Recommendations & Next Steps).
 */

const { Paragraph, TextRun, BorderStyle } = require('docx');
const { COLORS, FONTS, FONT_SIZES } = require('../styles');
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

function buildSection6(data, metadata) {
  const children = [];
  const layer1 = data.layer1_store_performance;
  const layer2 = data.layer2_module_analysis;
  const layer3 = data.layer3_risk_analysis;

  children.push(heading1('六、建议与下一步行动'));

  // Key findings summary
  children.push(heading2('6.1 本月关键发现'));

  const findings = [];

  // Average score finding
  if (layer1.monthly_average >= 90) {
    findings.push(`本月平均得分 ${layer1.monthly_average} 分，整体食品安全状况良好。`);
  } else if (layer1.monthly_average >= 80) {
    findings.push(`本月平均得分 ${layer1.monthly_average} 分，整体状况尚可，部分门店仍有提升空间。`);
  } else {
    findings.push(`本月平均得分 ${layer1.monthly_average} 分，低于80分标准线，需要重点关注。`);
  }

  // Trend finding
  if (layer1.average_trend != null) {
    if (layer1.average_trend > 0) {
      findings.push(`较上月提升 ${layer1.average_trend} 分，呈改善趋势。`);
    } else if (layer1.average_trend < 0) {
      findings.push(`较上月下降 ${Math.abs(layer1.average_trend)} 分，需关注退步原因。`);
    } else {
      findings.push('与上月持平。');
    }
  }

  // Critical items
  if (layer3.s_items_count > 0) {
    findings.push(`发现 ${layer3.s_items_count} 个S项（关键项），涉及食品安全核心风险，必须优先处理。`);
  }

  // Systemic modules
  if (layer2.systemic_modules && layer2.systemic_modules.length > 0) {
    findings.push(
      `${layer2.systemic_modules.join('、')} 模块为系统性问题（影响超过50%门店），建议开展专项整改。`
    );
  }

  // Top problem module
  if (layer2.modules.length > 0) {
    const top = layer2.modules[0];
    findings.push(
      `问题最集中模块为"${top.module_name}"（${top.issue_count} 个问题，影响 ${top.affected_store_count} 家门店）。`
    );
  }

  findings.forEach(f => children.push(bulletPoint(f)));
  children.push(spacer(200));

  // Priority action items
  children.push(heading2('6.2 优先行动项'));

  const actions = [];
  let priority = 1;

  // S-items must be addressed first
  if (layer3.s_items_count > 0) {
    actions.push({
      priority: priority++,
      urgency: '紧急',
      action: `立即处理 ${layer3.s_items_count} 个S项（关键项），确保2天内完成整改闭环`,
      owner: '门店经理 + QA主管',
      deadline: 'SLA: 2天',
    });
  }

  // Low-scoring stores
  const lowStores = layer1.store_scores.filter(s => s.latest_score < 80);
  if (lowStores.length > 0) {
    actions.push({
      priority: priority++,
      urgency: '高',
      action: `对 ${lowStores.length} 家低于80分门店（${lowStores.map(s => s.store_name).join('、')}）开展专项辅导`,
      owner: '区域经理 + QA',
      deadline: '1周内',
    });
  }

  // Systemic module fix
  if (layer2.systemic_modules && layer2.systemic_modules.length > 0) {
    actions.push({
      priority: priority++,
      urgency: '高',
      action: `针对系统性问题模块（${layer2.systemic_modules.join('、')}）制定统一整改标准并下发全部门店`,
      owner: 'QA部门',
      deadline: '2周内',
    });
  }

  // Top 3 modules
  const top3Mods = layer2.modules.slice(0, 3);
  if (top3Mods.length > 0) {
    actions.push({
      priority: priority++,
      urgency: '中',
      action: `加强 ${top3Mods.map(m => m.module_name).join('、')} 模块的日常检查频次和培训力度`,
      owner: '门店运营团队',
      deadline: '持续',
    });
  }

  // Declined stores
  if (layer1.most_declined) {
    actions.push({
      priority: priority++,
      urgency: '中',
      action: `关注退步门店 ${layer1.most_declined.name}（${layer1.most_declined.change} 分），分析退步原因并制定改善计划`,
      owner: '区域经理',
      deadline: '1周内',
    });
  }

  // Always recommend data system improvement
  actions.push({
    priority: priority++,
    urgency: '低',
    action: '推动QA系统升级，增加整改跟踪字段（责任归属、整改时限、验证结果），实现CAPA闭环管理',
    owner: 'IT + QA部门',
    deadline: '季度规划',
  });

  if (actions.length > 0) {
    const actionRows = actions.map(a => [
      `P${a.priority}`,
      a.urgency,
      a.action,
      a.owner,
      a.deadline,
    ]);

    children.push(
      buildTable(
        ['优先级', '紧急度', '行动项', '责任方', '时限'],
        actionRows,
        {
          colWidths: [8, 10, 42, 20, 12],
          cellFormatter: (value, rowIdx, colIdx) => {
            if (colIdx === 1) {
              const colorMap = {
                '紧急': COLORS.RED,
                '高': COLORS.WARNING,
                '中': COLORS.BLUE_ACCENT,
                '低': COLORS.TEXT_DARK,
              };
              return { color: colorMap[value] || COLORS.TEXT_DARK, bold: true };
            }
            if (colIdx === 2) {
              return { alignment: 'left' };
            }
            return {};
          },
        }
      )
    );
  }

  children.push(spacer(200));

  // Module-level improvement recommendations
  children.push(heading2('6.3 模块改善建议'));

  const moduleRecommendations = {
    '设备与工具': '建立设备定期维护保养台账，关键设备（冰箱、制冰机）每日检查记录。',
    '清洁消毒': '重新培训清洁消毒SOP，重点强调频次和浓度配比，增加突击检查。',
    '温控管理': '确保所有冷藏/冷冻设备温度监测正常，建议部署物联网温度监控。',
    '储存管理': '规范先进先出（FIFO）管理，定期盘点，确保标签完整。',
    '食品加工区域': '加强操作台清洁标准执行，防止交叉污染，检查防护设施完好性。',
    '水务与管道': '定期检查水过滤设备和管道，确保隔气装置有效，油脂阱按时清理。',
    '虫害防控': '确认虫害防控合同有效，检查防虫设施完整性，记录巡查日志。',
    '有效期管理': '执行每日效期检查制度，建立临期预警机制，严格执行废弃流程。',
    '人员卫生': '强化个人卫生培训，确保健康证有效，每日着装/洗手标准检查。',
    '化学品管理': '化学品专区专柜存放，标识清晰，MSDS文件齐全，使用记录完整。',
    '环境与客区': '保持客区清洁整齐，垃圾桶及时清理，照明设备完好。',
    '证照与规范': '建立证照有效期台账，提前30天预警续期，确保合规文件随时可查。',
  };

  // Only show recommendations for modules that have issues
  const affectedModules = layer2.modules.filter(m => m.issue_count > 0).slice(0, 6);
  affectedModules.forEach(mod => {
    const rec = moduleRecommendations[mod.module_name];
    if (rec) {
      children.push(bulletPoint(
        `${mod.module_name}：${rec}`
      ));
    }
  });

  children.push(spacer(200));

  // Closing
  children.push(new Paragraph({
    spacing: { before: 400 },
    border: {
      top: {
        style: BorderStyle.SINGLE,
        size: 6,
        color: COLORS.NAVY,
        space: 10,
      },
    },
    children: [],
  }));

  children.push(bodyText(
    `— 报告结束 — ${metadata.analysis_month_cn} —`,
    { alignment: 'center', color: COLORS.BLUE_ACCENT, italics: true }
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

module.exports = { buildSection6 };
