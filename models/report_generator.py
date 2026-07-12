"""
PDF Report Generator
Exports user progress reports with charts and statistics.
"""

import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io


class ReportGenerator:
    """Generate PDF progress reports for users."""

    def __init__(self, user_data: dict, program_data: dict, measurements: list):
        self.user_data = user_data
        self.program_data = program_data
        self.measurements = measurements
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Create custom styles for the report."""
        self.styles.add(ParagraphStyle(
            name='ArabicTitle',
            fontName='Helvetica-Bold',
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=20,
            alignment=1  # Center
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceBefore=15,
            spaceAfter=10
        ))
        self.styles.add(ParagraphStyle(
            name='BodyTextCustom',
            fontName='Helvetica',
            fontSize=11,
            textColor=colors.HexColor('#555555'),
            spaceAfter=8
        ))

    def generate(self, output_path: str = None) -> str:
        """
        Generate the PDF report.
        Returns the file path.
        """
        if not output_path:
            output_dir = 'reports'
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"progress_report_{timestamp}.pdf")

        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                rightMargin=2 * cm, leftMargin=2 * cm,
                                topMargin=2 * cm, bottomMargin=2 * cm)

        elements = []

        # Header
        elements.append(Paragraph("Fitness AI - Progress Report", self.styles['ArabicTitle']))
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y')}",
                                  self.styles['BodyTextCustom']))
        elements.append(Spacer(1, 1 * cm))

        # User Info Section
        elements.append(Paragraph("User Information", self.styles['SectionHeader']))
        user_info = [
            [Paragraph("Email:", self.styles['BodyTextCustom']),
             Paragraph(self.user_data.get('email', 'N/A'), self.styles['BodyTextCustom'])],
            [Paragraph("Phone:", self.styles['BodyTextCustom']),
             Paragraph(self.user_data.get('phone', 'N/A'), self.styles['BodyTextCustom'])],
        ]
        info_table = Table(user_info, colWidths=[4 * cm, 10 * cm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.5 * cm))

        # Program Progress Section
        if self.program_data:
            elements.append(Paragraph("Program Progress", self.styles['SectionHeader']))

            progress = self.program_data.get('progress', {})
            progress_text = f"""
            Total Workouts: {progress.get('total', 0)}<br/>
            Completed: {progress.get('completed', 0)}<br/>
            Progress: {progress.get('percentage', 0)}%<br/>
            """
            elements.append(Paragraph(progress_text, self.styles['BodyTextCustom']))

            # Add progress chart
            chart_image = self._create_progress_chart(progress)
            if chart_image:
                elements.append(Image(chart_image, width=15 * cm, height=6 * cm))
            elements.append(Spacer(1, 0.5 * cm))

        # Body Measurements Section
        if self.measurements and len(self.measurements) > 1:
            elements.append(Paragraph("Body Measurements History", self.styles['SectionHeader']))

            # Weight chart
            weight_chart = self._create_weight_chart()
            if weight_chart:
                elements.append(Image(weight_chart, width=15 * cm, height=6 * cm))

            # Measurements table
            elements.append(Paragraph("Recent Measurements:", self.styles['BodyTextCustom']))
            table_data = [["Date", "Weight (kg)", "Chest (cm)", "Waist (cm)", "Hips (cm)", "Arms (cm)", "Thighs (cm)"]]

            for m in self.measurements[:10]:
                table_data.append([
                    str(m.get('recorded_date', '')),
                    str(m.get('weight', '')),
                    str(m.get('chest', '-')),
                    str(m.get('waist', '-')),
                    str(m.get('hips', '-')),
                    str(m.get('arms', '-')),
                    str(m.get('thighs', '-'))
                ])
            for m in self.measurements[:10]:  # Last 10
                table_data.append([
                    str(m.get('recorded_date', '')),
                    str(m.get('weight', '')),
                    str(m.get('waist', '-')),
                    str(m.get('chest', '-')),
                    str(m.get('hips', '-'))
                ])

            if len(table_data) > 1:
                meas_table = Table(table_data, colWidths=[2.5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm])
                meas_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('PADDING', (0, 0), (-1, -1), 5),
                ]))
                elements.append(meas_table)

        # Build PDF
        doc.build(elements)
        return output_path

    def _create_progress_chart(self, progress: dict) -> io.BytesIO:
        """Create a donut chart for program progress."""
        try:
            fig, ax = plt.subplots(figsize=(6, 4))

            completed = progress.get('completed', 0)
            remaining = progress.get('total', 0) - completed

            sizes = [completed, remaining]
            colors_chart = ['#4caf50', '#e0e0e0']
            labels = ['Completed', 'Remaining']

            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors_chart,
                                              autopct='%1.0f%%', startangle=90,
                                              wedgeprops={'width': 0.4})

            ax.set_title('Program Completion', fontweight='bold', color='#333')

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', transparent=True)
            plt.close()
            buf.seek(0)
            return buf
        except:
            return None

    def _create_weight_chart(self):
        """Create a line chart for all measurements over time."""
        try:
            # Collect all measurement data
            dates = []
            weights = []
            chests = []
            waists = []
            hips_list = []
            arms_list = []
            thighs_list = []

            for m in self.measurements:
                recorded = m.get('recorded_date', '')
                if hasattr(recorded, 'strftime'):
                    dates.append(recorded.strftime('%Y-%m-%d'))
                elif isinstance(recorded, str):
                    dates.append(recorded)
                else:
                    dates.append(str(recorded))

                weights.append(float(m.get('weight', 0)) if m.get('weight') else None)
                chests.append(float(m.get('chest')) if m.get('chest') else None)
                waists.append(float(m.get('waist')) if m.get('waist') else None)
                hips_list.append(float(m.get('hips')) if m.get('hips') else None)
                arms_list.append(float(m.get('arms')) if m.get('arms') else None)
                thighs_list.append(float(m.get('thighs')) if m.get('thighs') else None)

            # Reverse to show oldest first
            dates.reverse()
            weights.reverse()
            chests.reverse()
            waists.reverse()
            hips_list.reverse()
            arms_list.reverse()
            thighs_list.reverse()

            # Limit to last 10 entries
            if len(dates) > 10:
                dates = dates[-10:]
                weights = weights[-10:]
                chests = chests[-10:]
                waists = waists[-10:]
                hips_list = hips_list[-10:]
                arms_list = arms_list[-10:]
                thighs_list = thighs_list[-10:]

            fig, ax = plt.subplots(figsize=(12, 6))

            x = range(len(dates))

            # Plot each measurement line
            lines = []

            if any(w is not None for w in weights):
                line, = ax.plot(x, weights, marker='o', color='#667eea', linewidth=2, markersize=5, label='Weight (kg)')
                lines.append(line)

            if any(c is not None for c in chests):
                line, = ax.plot(x, chests, marker='s', color='#e74c3c', linewidth=2, markersize=5, label='Chest (cm)')
                lines.append(line)

            if any(w is not None for w in waists):
                line, = ax.plot(x, waists, marker='^', color='#2ecc71', linewidth=2, markersize=5, label='Waist (cm)')
                lines.append(line)

            if any(h is not None for h in hips_list):
                line, = ax.plot(x, hips_list, marker='D', color='#f39c12', linewidth=2, markersize=5, label='Hips (cm)')
                lines.append(line)

            if any(a is not None for a in arms_list):
                line, = ax.plot(x, arms_list, marker='v', color='#9b59b6', linewidth=2, markersize=5, label='Arms (cm)')
                lines.append(line)

            if any(t is not None for t in thighs_list):
                line, = ax.plot(x, thighs_list, marker='*', color='#1abc9c', linewidth=2, markersize=5,
                                label='Thighs (cm)')
                lines.append(line)

            ax.set_ylabel('Measurements', fontweight='bold')
            ax.set_title('Body Measurements Progress', fontweight='bold', color='#333', fontsize=14)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='best')

            # Set x-axis labels
            if len(dates) > 5:
                ax.set_xticks(list(x))
                ax.set_xticklabels(dates, rotation=45, ha='right')
            else:
                ax.set_xticks(list(x))
                ax.set_xticklabels(dates)

            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', transparent=True)
            plt.close()
            buf.seek(0)
            return buf
        except Exception as e:
            print(f"Chart error: {e}")
            return None