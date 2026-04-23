#!/usr/bin/env python3
"""
Test script to check insights content and encoding
测试洞察内容和编码的脚本
"""

import os
import sys

# 设置环境变量
os.environ['MYSQL_USER'] = 'diagtools'
os.environ['MYSQL_PASSWORD'] = 'BPakqykn15SN!P9p'

# 导入报告生成器
import weekly_ops_report_generator as wrg
from datetime import datetime, timedelta

def main():
    print("=== 检查洞察内容和编码 ===")

    try:
        # 加载配置
        print("加载配置文件...")
        wrg.load_config('config.yaml')

        # 计算本周时间
        today = datetime.now()
        days_since_monday = today.weekday()
        if days_since_monday == 0 and today.hour < 9:
            week_start = today - timedelta(days=7)
        else:
            week_start = today - timedelta(days=days_since_monday + 7)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        print(f"报告周期: {week_start.strftime('%Y-%m-%d')}")

        # 数据收集
        print("连接数据库收集数据...")
        db = wrg.DatabaseClient(wrg.DB_CONFIGS)
        collector = wrg.DataCollector(db, week_start)
        data = collector.collect_all()

        # 生成洞察
        print("生成洞察分析...")
        analyzer = wrg.InsightEngine(data)
        insights = analyzer.analyze()

        print(f"\n=== 生成了 {len(insights)} 个洞察 ===")

        # 详细检查每个洞察
        for i, insight in enumerate(insights, 1):
            priority = insight.get('priority', '')
            title = insight.get('title', '')
            summary = insight.get('summary', '')
            detail = insight.get('detail', '')

            print(f"\n洞察 {i}:")
            print(f"  优先级: {priority}")
            print(f"  标题: {title}")
            print(f"  标题 (repr): {repr(title)}")
            print(f"  标题字节: {title.encode('utf-8') if title else None}")
            print(f"  摘要: {summary}")
            print(f"  详情: {detail}")

            # 检查是否有特殊字符
            if title:
                special_chars = [c for c in title if ord(c) > 127]
                if special_chars:
                    print(f"  包含特殊字符: {special_chars}")
                    print(f"  特殊字符码点: {[ord(c) for c in special_chars]}")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()