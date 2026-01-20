"""
报告生成 Agent
生成综合分析报告（支持 Markdown 和 HTML 格式）
"""

import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportAgent:
    """报告生成 Agent"""

    def __init__(self, config: Dict):
        """
        初始化报告生成 Agent

        Args:
            config: 配置字典，包含报告格式和内容配置
        """
        self.config = config
        self.report_config = config.get("report", {})
        self.format = self.report_config.get("format", "markdown")
        self.include_sections = self.report_config.get("include_sections", [])
        self.max_variants = self.report_config.get("max_variants_in_report", 10)

        logger.info(f"✓ 报告生成 Agent 初始化: format={self.format}")

    def execute(self, task: Dict) -> Dict:
        """
        执行报告生成任务

        Args:
            task: 任务字典，包含 scores_file, evidence_file 和 output 配置

        Returns:
            执行结果字典
        """
        try:
            input_data = task["input"]
            scores_file = input_data["scores_file"]
            evidence_file = input_data["evidence_file"]
            
            # 自动调整扩展名
            output_file = task["output"]["report_file"]
            if self.format == "html" and output_file.endswith(".md"):
                output_file = output_file.replace(".md", ".html")
            elif self.format == "markdown" and output_file.endswith(".html"):
                output_file = output_file.replace(".html", ".md")

            logger.info(f"→ 开始生成报告: {output_file}")

            # 读取数据
            scores_df = pd.read_csv(scores_file, sep='\t')
            with open(evidence_file, 'r', encoding='utf-8') as f:
                evidence_data = json.load(f)

            # 生成报告
            if self.format == "html":
                report_content = self._generate_html_report(scores_df, evidence_data)
            else:
                report_content = self._generate_markdown_report(scores_df, evidence_data)

            # 保存报告
            self._save_report(report_content, output_file)
            logger.info(f"✓ 报告生成完成: {output_file}")

            return {
                "status": "success",
                "output_files": {
                    "report_file": str(output_file)
                },
                "variants_reported": min(len(scores_df), self.max_variants)
            }

        except Exception as e:
            logger.error(f"✗ 报告生成失败: {e}")
            raise

    def _generate_markdown_report(self, scores_df: pd.DataFrame, evidence_data: Dict) -> str:
        """生成 Markdown 格式报告 (原有逻辑)"""
        lines = []

        # 标题
        lines.append("# Genos 基因组变异分析报告")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 摘要
        if "summary" in self.include_sections:
            lines.extend(self._generate_summary(scores_df))

        # Top 变异
        if "top_variants" in self.include_sections:
            lines.extend(self._generate_top_variants(scores_df, evidence_data))

        # 证据汇总
        if "evidence" in self.include_sections:
            lines.extend(self._generate_evidence_summary(evidence_data))

        # 建议
        if "recommendations" in self.include_sections:
            lines.extend(self._generate_recommendations(scores_df))

        return "\n".join(lines)

    def _generate_html_report(self, scores_df: pd.DataFrame, evidence_data: Dict) -> str:
        """生成易读的 HTML 报告"""
        
        # 1. 准备数据
        total = len(scores_df)
        high_impact = scores_df[scores_df["impact_level"] == "HIGH"]
        high_count = len(high_impact)
        moderate_count = len(scores_df[scores_df["impact_level"] == "MODERATE"])
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 2. HTML 模板
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Genos 基因检测分析报告</title>
    <style>
        :root {{
            --primary-color: #2c3e50;
            --accent-color: #3498db;
            --danger-color: #e74c3c;
            --warning-color: #f1c40f;
            --success-color: #27ae60;
            --bg-color: #f8f9fa;
            --card-bg: #ffffff;
            --text-color: #333333;
        }}
        
        body {{
            font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            margin: 0;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            padding: 40px 0;
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            color: white;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header p {{ opacity: 0.8; margin-top: 10px; }}
        
        .card {{
            background: var(--card-bg);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 25px;
        }}
        
        .card h2 {{
            color: var(--primary-color);
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        
        /* 概览卡片 */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            text-align: center;
        }}
        
        .stat-box {{
            padding: 20px;
            border-radius: 8px;
            background: #f8f9fa;
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: var(--accent-color);
        }}
        
        .stat-value.danger {{ color: var(--danger-color); }}
        
        /* 变异列表 */
        .variant-item {{
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            transition: transform 0.2s;
        }}
        
        .variant-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        
        .variant-item.high-impact {{
            border-left: 5px solid var(--danger-color);
        }}
        
        .variant-info h3 {{ margin: 0 0 5px 0; }}
        .variant-meta {{ color: #666; font-size: 0.9em; }}
        
        .badge {{
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            color: white;
            display: inline-block;
        }}
        
        .badge.high {{ background-color: var(--danger-color); }}
        .badge.moderate {{ background-color: var(--warning-color); color: #333; }}
        .badge.low {{ background-color: var(--success-color); }}

        .variant-details {{
            width: 100%;
            margin-top: 10px;
        }}

        .evidence-box {{
            margin-top: 12px;
            padding: 12px 16px;
            background: #f7fbff;
            border: 1px solid #e3effb;
            border-radius: 8px;
        }}

        .evidence-box h4 {{
            margin: 0 0 6px 0;
            font-size: 0.95em;
            color: #2c3e50;
        }}

        .evidence-list {{
            margin: 6px 0 0 18px;
            padding: 0;
            color: #444;
            font-size: 0.9em;
        }}

        .explanation-box {{
            margin-top: 12px;
            padding: 12px 16px;
            background: #fff8e8;
            border: 1px solid #ffe3b3;
            border-radius: 8px;
            font-size: 0.9em;
            color: #5a4a2c;
        }}
        
        /* 建议部分 */
        .recommendation-list li {{
            margin-bottom: 10px;
            padding-left: 10px;
        }}
        
        .glossary {{
            font-size: 0.9em;
            color: #666;
            background: #f9f9f9;
            padding: 15px;
            border-radius: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>基因检测分析简报</h1>
            <p>基于 Genos AI 智能分析系统 | 生成时间: {timestamp}</p>
        </header>

        <!-- 1. 结果概览 -->
        <div class="card">
            <h2>📊 结果概览</h2>
            <p>本次分析共检测了 <strong>{total}</strong> 个基因变异位点。以下是重点关注的发现：</p>
            
            <div class="summary-grid">
                <div class="stat-box">
                    <div class="stat-value danger">{high_count}</div>
                    <div class="stat-label">高风险变异</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{moderate_count}</div>
                    <div class="stat-label">中等风险变异</div>
                </div>
                 <div class="stat-box">
                    <div class="stat-value" style="color:var(--success-color)">{total - high_count - moderate_count}</div>
                    <div class="stat-label">低风险变异</div>
                </div>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background-color: #fff3cd; border-radius: 6px; color: #856404;">
                <strong>💡 什么是风险等级？</strong>
                <ul style="margin: 5px 0 0 20px">
                    <li><strong>高风险</strong>: 可能显著改变蛋白质功能，与潜在疾病风险高度相关。</li>
                    <li><strong>中等风险</strong>: 对蛋白质功能有一定影响，建议结合临床症状关注。</li>
                    <li><strong>低风险</strong>: 通常是良性的，对健康影响较小。</li>
                </ul>
            </div>
        </div>

        <!-- 2. 重点关注变异 -->
        <div class="card">
            <h2>🔍 重点关注发现</h2>
            <p>以下是系统筛选出的最需要关注的变异信息：</p>
            
            {self._generate_html_variants_list(scores_df, evidence_data)}
        </div>

        <!-- 3. 行动建议 -->
        <div class="card">
            <h2>👩‍⚕️ 下一步建议</h2>
            <ul class="recommendation-list">
                {self._generate_html_recommendations(high_count, moderate_count)}
            </ul>
        </div>
        
        <div class="card glossary">
            <h3>📖 小词典</h3>
            <p><strong>Ref (参考)</strong>: 大多数人该位置的基因序列。</p>
            <p><strong>Alt (变异)</strong>: 检测到的您的基因序列。</p>
            <p><strong>Genos 评分</strong>: AI 模型预测的致病概率，分数越高(0-1)风险越大。</p>
        </div>
        
        <footer style="text-align: center; color: #999; margin-top: 40px;">
            <p>注意：本报告由 AI 系统自动生成，仅供科研参考，不可作为最终临床诊断依据。</p>
        </footer>
    </div>
</body>
</html>
        """
        return html

    def _generate_html_variants_list(self, scores_df: pd.DataFrame, evidence_data: Dict) -> str:
        """生成 HTML 变异列表"""
        html_items = []

        # 取 Top N
        top_variants = scores_df.nlargest(self.max_variants, "final_score")

        for _, variant in top_variants.iterrows():
            vid = variant["variant_id"]
            chrom = variant["chrom"]
            pos = variant["pos"]
            ref = variant["ref"]
            alt = variant["alt"]
            score = variant["final_score"]
            impact = variant["impact_level"]
            gene = variant.get("gene", "")

            # 格式化
            impact_class = "high" if impact == "HIGH" else ("moderate" if impact == "MODERATE" else "low")
            impact_text = "高风险" if impact == "HIGH" else ("中等风险" if impact == "MODERATE" else "低风险")

            # 获取证据
            evidence_key = str(vid)
            evidence = evidence_data.get(evidence_key, evidence_data.get(vid, {}))
            sources = evidence.get("sources", [])
            source_names = [s["source"] for s in sources if s["source"] != "Prediction"]
            evidence_tag = f"<br><small>📚 证据来源: {', '.join(source_names)}</small>" if source_names else ""

            gene_label = f" | 基因: <strong>{gene}</strong>" if isinstance(gene, str) and gene else ""

            # 【新增】获取AI通俗化解释
            gene_explanation = evidence.get("gene_explanation")
            explanation_html = ""

            if gene_explanation:
                explanation_html = f"""
                <div style="margin-top: 15px; padding: 20px; background: linear-gradient(135deg, #f0f8ff 0%, #e6f2ff 100%); border-left: 5px solid #3498db; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="display: flex; align-items: center; margin-bottom: 12px;">
                        <span style="font-size: 1.3em; margin-right: 8px;">🤖</span>
                        <h4 style="margin: 0; color: #2c3e50; font-size: 1.1em;">AI 通俗化解释</h4>
                    </div>
                    <div style="white-space: pre-line; line-height: 1.9; color: #34495e; font-size: 0.95em;">
                        {gene_explanation}
                    </div>
                    <div style="margin-top: 12px; padding-top: 12px; border-top: 1px dashed #ccc; font-size: 0.85em; color: #7f8c8d; font-style: italic;">
                        💡 此解释由 DeepSeek AI 自动生成，仅供参考理解，不作为临床诊断依据
                    </div>
                </div>
                """

            # 评分解释（LLM 输出）
            llm_explanation = variant.get("explanation", "")
            llm_explanation_html = ""
            if isinstance(llm_explanation, str) and llm_explanation.strip():
                llm_explanation_html = f"""
                <div class="explanation-box">
                    <strong>评分解释:</strong> {llm_explanation}
                </div>
                """

            # 证据详情（RAG）
            evidence_detail_html = self._generate_html_evidence_detail(evidence)

            item_html = f"""
            <div class="variant-item {impact_class}-impact" style="margin-bottom: 25px;">
                <div class="variant-info">
                    <h3>{vid} <span style="font-weight:normal; font-size:0.8em; color:#888;">({chrom}:{pos})</span></h3>
                    <div class="variant-meta">
                        基因变化: <strong>{ref}</strong> &rarr; <strong>{alt}</strong>{gene_label}
                        {evidence_tag}
                    </div>
                </div>
                <div class="variant-score" style="text-align:right">
                    <span class="badge {impact_class}">{impact_text}</span>
                    <div style="font-size: 0.8em; color: #666; margin-top: 5px;">AI 评分: {score:.2f}</div>
                </div>

                <div class="variant-details">
                    {llm_explanation_html}
                    {evidence_detail_html}
                    {explanation_html}
                </div>
            </div>
            """
            html_items.append(item_html)

        return "\n".join(html_items)

    def _generate_html_evidence_detail(self, evidence: Dict) -> str:
        """生成 HTML 证据详情"""
        if not evidence:
            return ""

        sources = evidence.get("sources", [])
        if not sources:
            return ""

        items = []
        for source in sources:
            name = source.get("source", "")
            data = source.get("data", {}) or {}

            if name == "ClinVar":
                if data.get("found"):
                    sig = data.get("clinical_significance") or data.get("significance") or "N/A"
                    disease = data.get("disease_name") or "N/A"
                    items.append(f"ClinVar: {sig}; {disease}")
                else:
                    msg = data.get("message", "Not found")
                    items.append(f"ClinVar: {msg}")
            elif name == "gnomAD":
                if data.get("found"):
                    af = data.get("allele_frequency", 0.0)
                    items.append(f"gnomAD: AF={af:.6g}")
                else:
                    items.append("gnomAD: Not found")
            elif name == "OMIM":
                if data.get("found"):
                    diseases = data.get("diseases", [])
                    disease_text = ", ".join(diseases) if diseases else "No disease link"
                    items.append(f"OMIM: {disease_text}")
                else:
                    items.append("OMIM: Not found")
            elif name == "Prediction":
                score = data.get("final_score", "")
                impact = data.get("impact_level", "")
                items.append(f"Prediction: score={score}, impact={impact}")
            else:
                items.append(f"{name}: {data}")

        if not items:
            return ""

        evidence_items = "\n".join(f"<li>{item}</li>" for item in items)
        return f"""
        <div class="evidence-box">
            <h4>RAG 证据汇总</h4>
            <ul class="evidence-list">
                {evidence_items}
            </ul>
        </div>
        """

    def _generate_html_recommendations(self, high_count: int, moderate_count: int) -> str:
        """生成 HTML 格式建议"""
        items = []
        
        if high_count > 0:
            items.append("<li><strong>咨询遗传咨询师</strong>: 您有高风险变异，建议寻求专业遗传咨询师解读。</li>")
            items.append("<li><strong>临床验证</strong>: 建议使用一代测序(Sanger)验证该位点是否真实存在。</li>")
            
        if moderate_count > 0:
            items.append("<li><strong>关注相关症状</strong>: 请留意是否出现与该基因相关的身体特征或症状。</li>")
            
        items.append("<li><strong>保持健康生活</strong>: 基因只是影响健康的一部分，良好的生活习惯同样重要。</li>")
        items.append("<li><strong>定期体检</strong>: 建议每年进行一次全面体检。</li>")
        
        return "\n".join(items)

    # 保留原有的辅助方法用于 Markdown 生成
    def _generate_summary(self, scores_df: pd.DataFrame) -> List[str]:
        """生成分析摘要"""
        lines = ["## 分析摘要", ""]

        total = len(scores_df)
        high = len(scores_df[scores_df["impact_level"] == "HIGH"])
        moderate = len(scores_df[scores_df["impact_level"] == "MODERATE"])
        low = len(scores_df[scores_df["impact_level"] == "LOW"])

        lines.append(f"- **总变异数**: {total}")
        lines.append(f"- **高影响变异**: {high} ({high/total*100:.1f}%)")
        lines.append(f"- **中等影响变异**: {moderate} ({moderate/total*100:.1f}%)")
        lines.append(f"- **低影响变异**: {low} ({low/total*100:.1f}%)")
        lines.append("")
        return lines

    def _generate_top_variants(self, scores_df: pd.DataFrame, evidence_data: Dict) -> List[str]:
        """生成 Top 变异列表"""
        lines = [f"## Top {self.max_variants} 高影响变异", ""]
        top_variants = scores_df.nlargest(self.max_variants, "final_score")
        lines.append("| Rank | 变异 ID | 位置 | Ref→Alt | 评分 | 影响等级 | 证据来源 |")
        lines.append("|------|---------|------|---------|------|----------|----------|")
        for idx, (_, variant) in enumerate(top_variants.iterrows(), 1):
            vid = variant["variant_id"]
            chrom = variant["chrom"]
            pos = variant["pos"]
            ref = variant["ref"]
            alt = variant["alt"]
            score = variant["final_score"]
            impact = variant["impact_level"]
            evidence_key = str(vid)
            evidence = evidence_data.get(evidence_key, evidence_data.get(vid, {}))
            sources = evidence.get("sources", [])
            source_names = ", ".join([s["source"] for s in sources[:3]])
            lines.append(f"| {idx} | {vid} | {chrom}:{pos} | {ref}→{alt} | {score:.3f} | {impact} | {source_names} |")
        lines.append("")
        return lines

    def _generate_evidence_summary(self, evidence_data: Dict) -> List[str]:
        lines = ["## 证据汇总", ""]
        source_counts = {}
        for vid, evidence in evidence_data.items():
            for source in evidence.get("sources", []):
                source_name = source["source"]
                source_counts[source_name] = source_counts.get(source_name, 0) + 1
        lines.append("**证据来源统计**:")
        for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- {source}: {count} 个变异")
        lines.append("")
        return lines

    def _generate_recommendations(self, scores_df: pd.DataFrame) -> List[str]:
        lines = ["## 建议", ""]
        high_variants = scores_df[scores_df["impact_level"] == "HIGH"]
        if len(high_variants) > 0:
            lines.append("### 高影响变异")
            lines.append(f"发现 {len(high_variants)} 个高影响变异，建议:")
            lines.append("1. 进行实验验证（Sanger 测序确认）")
        return lines

    def _save_report(self, content: str, output_file: str):
        """保存报告"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
