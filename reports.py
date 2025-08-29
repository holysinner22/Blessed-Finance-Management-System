# reports.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from db import get_db_connection
from datetime import date, timedelta
import matplotlib.pyplot as plt
import os

class ReportManagement:
    @staticmethod
    def generate_report(root, user_role):
        report_window = tk.Toplevel(root)
        report_window.title("Generate Reports")
        report_window.state("zoomed")
        report_window.configure(bg="#1a1a2e")

        style = ttk.Style(report_window)
        style.configure('TLabel', background='#1a1a2e', foreground='white', font=('Helvetica', 12))
        style.configure('TButton', background='#e94560', foreground='white', font=('Helvetica', 12, 'bold'))

        ttk.Label(report_window, text="Select Report Type:").pack(anchor="w", padx=20, pady=10)
        report_type = ttk.Combobox(report_window, values=["Payment Report", "Expense Report"])
        report_type.set("Payment Report")
        report_type.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(report_window, text="Select Class (Optional):").pack(anchor="w", padx=20, pady=10)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT class FROM students")
        classes = ["All Classes"] + [r[0] for r in cursor.fetchall() if r[0]]
        conn.close()
        class_combo = ttk.Combobox(report_window, values=classes)
        class_combo.set("All Classes")
        class_combo.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(report_window, text="Select Period (For Expenses):").pack(anchor="w", padx=20, pady=10)
        period_combo = ttk.Combobox(report_window, values=["All", "Daily", "Weekly", "Monthly"])
        period_combo.set("All")
        period_combo.pack(fill=tk.X, padx=20, pady=5)

        def generate_pdf():
            rpt = report_type.get()
            selected_class = class_combo.get()
            period = period_combo.get()

            file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
            if not file_path:
                return

            doc = SimpleDocTemplate(file_path, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()

            # Header
            title = f"{rpt} - {selected_class if selected_class != 'All Classes' else 'All Classes'}"
            elements.append(Paragraph(title, styles['Title']))
            elements.append(Spacer(1, 12))

            conn = get_db_connection()
            cursor = conn.cursor()

            if rpt == "Payment Report":
                query = """
                    SELECT f.id, s.name, s.class, fc.name, f.term, f.required_amount, f.paid_amount,
                           (f.required_amount - f.paid_amount)
                    FROM fees f
                    JOIN students s ON f.student_id = s.id
                    JOIN fee_categories fc ON f.category_id = fc.id
                """
                params = []
                if selected_class != "All Classes":
                    query += " WHERE s.class = ?"
                    params.append(selected_class)
                query += " ORDER BY s.class, s.name"
                cursor.execute(query, params)
                rows = cursor.fetchall()

                data = [["ID","Student Name","Class","Category","Term","Required","Paid","Balance"]]
                for row in rows:
                    data.append([
                        row[0], row[1], row[2], row[3], row[4] or "N/A",
                        f"TZS {row[5]:,.2f}", f"TZS {row[6]:,.2f}", f"TZS {row[7]:,.2f}"
                    ])

            else:  # Expense Report
                query = "SELECT id, item, quantity, cost, (quantity * cost), date FROM expenses WHERE 1=1"
                params = []
                today = date.today()
                if period != "All":
                    if period == "Daily":
                        query += " AND date = ?"
                        params.append(today.isoformat())
                    elif period == "Weekly":
                        week_start = today - timedelta(days=today.weekday())
                        query += " AND date BETWEEN ? AND ?"
                        params.extend([week_start.isoformat(), today.isoformat()])
                    elif period == "Monthly":
                        month_start = today.replace(day=1)
                        query += " AND date BETWEEN ? AND ?"
                        params.extend([month_start.isoformat(), today.isoformat()])
                query += " ORDER BY date DESC"
                cursor.execute(query, params)
                rows = cursor.fetchall()

                data = [["ID","Item","Qty","Cost/Unit","Total","Date"]]
                for row in rows:
                    data.append([row[0], row[1], row[2], f"TZS {row[3]:,.2f}", f"TZS {row[4]:,.2f}", row[5]])

                # Prepare chart for expenses
                if rows:
                    categories = {}
                    for r in rows:
                        categories[r[1]] = categories.get(r[1], 0) + r[4]

                    # Bar chart
                    fig, ax = plt.subplots(figsize=(6,3))
                    ax.bar(categories.keys(), categories.values(), color='skyblue')
                    ax.set_title('Expenses by Item', fontsize=14)
                    ax.set_ylabel('Total TZS')
                    ax.tick_params(axis='x', rotation=45)
                    chart_file = "expense_chart.png"
                    plt.tight_layout()
                    plt.savefig(chart_file)
                    plt.close()

                    elements.append(Image(chart_file, width=400, height=200))
                    elements.append(Spacer(1, 12))

            conn.close()

            # Summary
            total_amount = sum([row[-2] if rpt=="Expense Report" else row[-1] for row in rows]) if rows else 0
            elements.append(Paragraph(f"Total Records: {len(rows)}", styles['Normal']))
            elements.append(Paragraph(f"Total Amount: TZS {total_amount:,.2f}", styles['Normal']))
            elements.append(Spacer(1, 12))

            # Table
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#007bff")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
            ]))
            elements.append(table)

            # Footer
            elements.append(Spacer(1,12))
            elements.append(Paragraph("Generated by Blessed Finance System - © 2025", styles['Normal']))

            doc.build(elements)

            # Remove temp chart
            if rpt == "Expense Report" and os.path.exists("expense_chart.png"):
                os.remove("expense_chart.png")

            messagebox.showinfo("Success", f"{rpt} saved at:\n{file_path}")

        ttk.Button(report_window, text="Generate PDF", command=generate_pdf).pack(pady=30)
