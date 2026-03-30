// Channel Attribution V2 — Monthly Data (Exclusion Method)
// Generated: 2026-03-26
// Source: aws-luckyus-salescrm-rw / luckyus_sales_crm
// Methodology: Timing proxy Model B (conservative, iOS baseline) + 5.3% GGLMAP estimate from CDP sample

export const monthlyData = [
  {
    month: '2025-06', label: 'Jun 25',
    total: 8089, ios: 7084, android: 817, h5Total: 188,
    referral: 0, qrScan: 38, googleMaps: 10, socialOther: 140,
    organicTotal: 7939, marketingTotal: 150,
    organicPct: 98.1, marketingPct: 1.9,
    h5NrFastRate: 28.7, iosBaseline: 11.4, qrSharePct: 20.3,
  },
  {
    month: '2025-07', label: 'Jul 25',
    total: 23191, ios: 18552, android: 1999, h5Total: 2640,
    referral: 0, qrScan: 270, googleMaps: 140, socialOther: 2230,
    organicTotal: 20821, marketingTotal: 2370,
    organicPct: 89.8, marketingPct: 10.2,
    h5NrFastRate: 70.2, iosBaseline: 67.1, qrSharePct: 10.2,
  },
  {
    month: '2025-08', label: 'Aug 25',
    total: 24570, ios: 19530, android: 1984, h5Total: 3054,
    referral: 340, qrScan: 544, googleMaps: 162, socialOther: 2010,
    organicTotal: 22058, marketingTotal: 2512,
    organicPct: 89.8, marketingPct: 10.2,
    h5NrFastRate: 78.0, iosBaseline: 73.3, qrSharePct: 20.1,
  },
  {
    month: '2025-09', label: 'Sep 25',
    total: 27876, ios: 19541, android: 2243, h5Total: 6091,
    referral: 2137, qrScan: 909, googleMaps: 323, socialOther: 2723,
    organicTotal: 22693, marketingTotal: 5183,
    organicPct: 81.4, marketingPct: 18.6,
    h5NrFastRate: 79.8, iosBaseline: 74.7, qrSharePct: 23.0,
  },
  {
    month: '2025-10', label: 'Oct 25',
    total: 21993, ios: 14558, android: 1754, h5Total: 5681,
    referral: 2162, qrScan: 1067, googleMaps: 301, socialOther: 2151,
    organicTotal: 17379, marketingTotal: 4614,
    organicPct: 79.0, marketingPct: 21.0,
    h5NrFastRate: 83.0, iosBaseline: 76.9, qrSharePct: 30.3,
  },
  {
    month: '2025-11', label: 'Nov 25',
    total: 17506, ios: 11556, android: 1452, h5Total: 4498,
    referral: 1615, qrScan: 469, googleMaps: 238, socialOther: 2176,
    organicTotal: 13477, marketingTotal: 4029,
    organicPct: 77.0, marketingPct: 23.0,
    h5NrFastRate: 82.7, iosBaseline: 79.9, qrSharePct: 16.3,
  },
  {
    month: '2025-12', label: 'Dec 25',
    total: 22704, ios: 14989, android: 1881, h5Total: 5834,
    referral: 1981, qrScan: 813, googleMaps: 309, socialOther: 2731,
    organicTotal: 17683, marketingTotal: 5021,
    organicPct: 77.9, marketingPct: 22.1,
    h5NrFastRate: 83.6, iosBaseline: 80.0, qrSharePct: 21.1,
  },
  {
    month: '2026-01', label: 'Jan 26',
    total: 19226, ios: 12520, android: 1530, h5Total: 5176,
    referral: 1549, qrScan: 551, googleMaps: 274, socialOther: 2802,
    organicTotal: 14601, marketingTotal: 4625,
    organicPct: 75.9, marketingPct: 24.1,
    h5NrFastRate: 83.5, iosBaseline: 81.1, qrSharePct: 15.2,
  },
  {
    month: '2026-02', label: 'Feb 26',
    total: 18121, ios: 11768, android: 1338, h5Total: 5015,
    referral: 1356, qrScan: 1858, googleMaps: 266, socialOther: 1535,
    organicTotal: 14964, marketingTotal: 3157,
    organicPct: 82.6, marketingPct: 17.4,
    h5NrFastRate: 89.7, iosBaseline: 82.1, qrSharePct: 50.8,
  },
  {
    month: '2026-03', label: 'Mar 26',
    total: 22103, ios: 14567, android: 1550, h5Total: 5986,
    referral: 1557, qrScan: 2081, googleMaps: 317, socialOther: 2031,
    organicTotal: 18198, marketingTotal: 3905,
    organicPct: 82.3, marketingPct: 17.7,
    h5NrFastRate: 90.7, iosBaseline: 85.2, qrSharePct: 47.0,
  },
];

// Grand totals
export const grandTotals = {
  total: 205379,
  organicTotal: 169813,
  marketingTotal: 35566,
  organicPct: 82.7,
  marketingPct: 17.3,
};

// Latest month (for KPI cards)
export const latestMonth = monthlyData[monthlyData.length - 1];
export const prevMonth = monthlyData[monthlyData.length - 2];
export const momChange = +(latestMonth.marketingPct - prevMonth.marketingPct).toFixed(1);

// Chart colors
export const COLORS = {
  primary: '#0365C0',
  navy: '#1A365D',
  teal: '#00A5A5',
  gold: '#DCBD23',
  bg: '#f8f9fb',
  card: '#FFFFFF',
  text: '#1f2937',
  textLight: '#6b7280',
  border: '#e5e7eb',
  // Organic channels (cool)
  iosOrganic: '#93C5FD',       // light blue
  androidOrganic: '#6EE7B7',   // light green
  qrScan: '#A5B4FC',           // light indigo
  // Marketing channels (warm)
  referral: '#FCA5A5',         // light red
  googleMaps: '#FDBA74',       // light orange
  socialOther: '#FDE68A',      // light yellow
  // Status
  up: '#10B981',
  down: '#EF4444',
};

// Methodology notes
export const methodology = {
  exclusionMethod: '排除法：从总注册量中减去营销团队明确未影响的渠道（iOS/Android有机下载 + 门店QR扫码），剩余部分 = 营销团队可归因渠道。',
  timingProxy: '时间代理模型：通过注册到首单时间（≤15分钟）的比率差异估算QR扫码用户。使用双组分混合模型（Model B，iOS基线，保守估计）。',
  gglmapNote: 'Google Maps估算基于2026年3月19日单日CDP样本（H5用户的5.3%），置信度较低。',
  floorEstimate: '营销贡献占比为下限估算。部分iOS/Android下载实际由营销驱动（如用户看到TikTok后去App Store搜索下载），但无Adjust SDK无法区分。',
  limitations: [
    '无法区分App Store/Play Store中付费与有机下载（需部署Adjust SDK）',
    '无法按触点细分QR扫码来源（需产品侧开发src参数埋点，预计4-6周）',
    'Google Maps估算基于单日CDP样本（n≈20），置信度低',
    '部分iOS/Android下载由营销驱动但被计入有机渠道（保守估计）',
    '2025年6-7月数据为早期运营阶段，推荐计划尚未启动',
  ],
  recommendations: [
    { title: '部署Adjust SDK', desc: '区分App Store/Play Store中付费与有机下载，提升归因精度', priority: '高', timeline: '2-3个月' },
    { title: 'QR码src参数埋点', desc: '区分门店不同触点（A-frame、柜台、桌面）的扫码来源', priority: '高', timeline: '4-6周' },
    { title: '积累CDP数据', desc: '持续收集CDP事件数据，提升Google Maps等渠道估算置信度', priority: '中', timeline: '持续' },
    { title: 'Redshift数据验证', desc: '获取Redshift访问权限，使用Sensors Data事件级数据交叉验证', priority: '中', timeline: '1-2周' },
  ],
};
