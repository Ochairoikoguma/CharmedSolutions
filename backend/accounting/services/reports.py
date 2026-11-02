#BytesIo provides a temp file like container in memory
#Used to build PDF without saving it to the disk first
from io import BytesIO
from xml.sax.saxutils import escape

#standard letter paper dimensions
from reportlab.lib.pagesizes import letter

#tools for drawing text and lines on the PDF
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


def generate_remittance_pdf(
    client_name,
    reporting_month,
    gross_recoveries,
    commission,
    applied_costs,
    net_remittance,
    net_recoveries,
    commission_rate,
    report_date,
    payments,
    costs,
    payment_client_total,
):

    """Create a PDF using totals supplied by the calculation service"""

    #create a container that will hold the PDF contents
    buffer = BytesIO()

    #Create a PDF drawing surface that writes into the container
    # SimpleDocTemplate arranges content and handles additional pages.
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    #set the doc title stored in the PDFs metadata
    pdf.title = "Remittance Report"

    navy = colors.HexColor("#001F3F")
    green = colors.HexColor("#00804C")
    cream = colors.HexColor("#F6F7ED")

    styles = getSampleStyleSheet()
    styles["Title"].textColor = navy
    styles["Title"].alignment = 0
    styles["Heading2"].textColor = navy

    # Small, wrapping text keeps long names inside table cells.
    styles.add(
        ParagraphStyle(
            name="TableText",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeading",
            parent=styles["TableText"],
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )
    )

    # Escape characters such as & so names display as ordinary text.
    def text_cell(value, style="TableText"):
        return Paragraph(escape(str(value)), styles[style])

    def money(value):
        return f"${value:,.2f}"

    # Build consistently styled tables with repeated column headings.
    def statement_table(headings, data, widths, money_start):
        heading_row = [
            text_cell(heading, "TableHeading")
            for heading in headings
        ]

        table = Table(
            [heading_row] + data,
            colWidths=widths,
            repeatRows=1,
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), green),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (money_start, 1), (-1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, cream],
                    ),
                    (
                        "LINEBELOW",
                        (0, 0),
                        (-1, 0),
                        0.5,
                        green,
                    ),
                ]
            )
        )

        return table

    # Add a page number to every page.
    def draw_footer(page_canvas, document):
        page_canvas.saveState()
        page_canvas.setFont("Helvetica", 8)
        page_canvas.setFillColor(navy)
        page_canvas.drawString(40, 22, "Regent & Associates")
        page_canvas.drawRightString(
            letter[0] - 40,
            22,
            f"Page {document.page}",
        )
        page_canvas.restoreState()

    # The report date is separate from the month being reported.
    # Pass a date object when calling this function.
    date_text = (
        f"{report_date:%B} {report_date.day}, {report_date.year}"
    )

    content = [
        Paragraph("REGENT &amp; ASSOCIATES", styles["Title"]),
        Paragraph(
            "Law Offices | 4151 Southwest Fwy, Suite 395",
            styles["Normal"],
        ),
        Paragraph("Houston, TX 77027", styles["Normal"]),
        Spacer(1, 28),
    ]

    # Identify the client receiving this report.
    content.append(
        Paragraph(escape(client_name), styles["Heading2"])
    )

    # Frame the report title, client name, and reporting month.
    content.extend(
        [
            Paragraph("Remittance Report", styles["Heading2"]),
            Paragraph(
                f"Reporting period: {escape(reporting_month)}",
                styles["Normal"],
            ),
            Paragraph(
                f"Report date: {date_text}",
                styles["Normal"],
            ),
            Spacer(1, 24),
        ]
    )

    #calculation service will provide these totals
    #Net recoveries is gross recoveries minus applied costs, before commission
    rows = [
        ("Gross Recoveries", gross_recoveries),
        ("Less Costs", applied_costs),
        ("Net Recoveries", net_recoveries),
        (
            f"Less Commission at {commission_rate:.2%}",
            commission,
        ),
        ("NET REMIT TO CLIENT", net_remittance),
    ]

    summary_data = []

    #Draw one label and amount for each row
    for label, amount in rows:
        #Parentheses identify deductions without changing their values.
        amount_text = (
            f"({money(amount)})"
            if label.startswith("Less")
            else money(amount)
        )
        summary_data.append([label, amount_text])

    summary = Table(
        summary_data,
        colWidths=[360, 172],
        hAlign="LEFT",
    )

    summary.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),

                #add space before next row
                ("TOPPADDING", (0, 0), (-1, -1), 13),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 13),

                ("LINEABOVE", (0, 2), (-1, 2), 0.5, colors.lightgrey),
                ("BACKGROUND", (0, -1), (-1, -1), cream),
                ("TEXTCOLOR", (0, -1), (-1, -1), navy),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, green),
            ]
        )
    )

    content.append(summary)

    #  Start the payment statement on a separate page
    content.extend(
        [
            PageBreak(),
            Paragraph("Client Payment Statement", styles["Heading2"]),
            Paragraph(escape(client_name), styles["Normal"]),
            Paragraph(escape(reporting_month), styles["Normal"]),
            Spacer(1, 16),
        ]
    )

    #Each payment supplies its already-calculated attorney/client shares
    payment_rows = [
        [
            text_cell(payment["debtor"]),
            text_cell(payment["claim_number"]),
            text_cell(payment["date"].strftime("%m/%d/%Y")),
            text_cell(payment["description"]),
            money(payment["amount"]),
            money(payment["attorney_share"]),
            money(payment["client_share"]),
        ]
        for payment in payments
    ]

    if payment_rows:
        content.append(
            statement_table(
                [
                    "Debtor", "Claim #", "Date", "Description",
                    "Amount", "Attorney", "Client",
                ],
                payment_rows,
                [140, 55, 60, 70, 69, 69, 69],
                money_start=4,
            )
        )
    else:
        content.append(
            Paragraph(
                "No payments included for this reporting period.",
                styles["Normal"],
            )
        )

    #Totals are supplied by the calculation service
    #Client share here is BEFORE costs, unlike net remittance
    content.extend(
        [
            Spacer(1, 14),
            Paragraph(
                f"<b>Total payments:</b> {money(gross_recoveries)}"
                f"<br/><b>Attorney share:</b> {money(commission)}"
                f"<br/><b>Client share before costs:</b> "
                f"{money(payment_client_total)}",
                styles["Normal"],
            ),
        ]
    )

    #Start the cost statement on another separate page
    content.extend(
        [
            PageBreak(),
            Paragraph("Client Cost Statement", styles["Heading2"]),
            Paragraph(escape(client_name), styles["Normal"]),
            Paragraph(escape(reporting_month), styles["Normal"]),
            Spacer(1, 16),
        ]
    )

    # Only pass costs applied to this report, excluding deferred costs
    cost_rows = [
        [
            text_cell(cost["debtor"]),
            text_cell(cost["claim_number"]),
            text_cell(cost["date"].strftime("%m/%d/%Y")),
            text_cell(cost["description"]),
            money(cost["amount"]),
        ]
        for cost in costs
    ]

    if cost_rows:
        content.append(
            statement_table(
                ["Debtor", "Claim #", "Date", "Description", "Amount"],
                cost_rows,
                [170, 65, 65, 147, 85],
                money_start=4,
            )
        )
    else:
        content.append(
            Paragraph(
                "No costs applied for this reporting period.",
                styles["Normal"],
            )
        )

    content.extend(
        [
            Spacer(1, 14),
            Paragraph(
                f"<b>Total costs applied:</b> {money(applied_costs)}",
                styles["Normal"],
            ),
        ]
    )

    #Build the entire report, including any extra statement pages
    pdf.build(
        content,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
    )

    return buffer.getvalue()