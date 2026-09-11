from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.units import mm

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///minds_facturen_app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

BTW_PERCENTAGE = 0.21

SELLER = {
    "name": "Minds Agency",
    "kvk": "95833455",
    "address1": "Jan Bijhouwerstraat 32",
    "address2": "1447GV Purmerend",
    "iban": "NL76BUNQ2196572136",
}

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    contact_name = db.Column(db.String(150), nullable=True)
    address1 = db.Column(db.String(150), nullable=True)
    address2 = db.Column(db.String(150), nullable=True)
    address3 = db.Column(db.String(150), nullable=True)
    kvk = db.Column(db.String(50), nullable=True)
    btw = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(80), nullable=True)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    customer = db.relationship("Customer", backref="invoices")
    invoice_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")

    @property
    def subtotal(self):
        return round(sum(line.total_ex_vat for line in self.lines), 2)

    @property
    def vat(self):
        return round(self.subtotal * BTW_PERCENTAGE, 2)

    @property
    def total(self):
        return round(self.subtotal + self.vat, 2)

    @property
    def is_overdue(self):
        return self.status == "open" and self.due_date < date.today()

    @property
    def days_overdue(self):
        if self.status != "open":
            return 0
        return max((date.today() - self.due_date).days, 0)

    @property
    def days_until_due(self):
        if self.status != "open":
            return None
        return (self.due_date - date.today()).days

    @property
    def crm_message(self):
        if self.status == "paid":
            return "Betaald"
        if self.status == "concept":
            return "Concept"
        days = self.days_until_due
        if days < 0:
            return f"{abs(days)} dagen over datum"
        if days == 0:
            return "Vervalt vandaag"
        if days == 1:
            return "Vervalt morgen"
        return f"Nog {days} dagen"

class InvoiceLine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    invoice = db.relationship("Invoice", backref="lines")
    quantity = db.Column(db.Float, nullable=False, default=1)
    description = db.Column(db.String(250), nullable=False)
    price_ex_vat = db.Column(db.Float, nullable=False)

    @property
    def total_ex_vat(self):
        return round(self.quantity * self.price_ex_vat, 2)

def euro(value):
    text = f"€ {value:,.2f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")

def parse_amount(value):
    return float((value or "0").replace("€", "").replace(" ", "").replace(".", "").replace(",", "."))

def next_invoice_no():
    invoices = Invoice.query.all()
    max_no = 0
    current_year = date.today().year
    for inv in invoices:
        try:
            year, number = inv.invoice_no.split("-")
            if int(year) == current_year:
                max_no = max(max_no, int(number))
        except Exception:
            pass
    if current_year == 2026 and max_no < 12:
        max_no = 12
    return f"{current_year}-{max_no + 1:03d}"

def get_or_create_otera():
    otera = Customer.query.filter_by(company_name="Otera B.V.").first()
    if otera:
        return otera
    otera = Customer(
        company_name="Otera B.V.",
        address1="Westerweg 198 C",
        address2="1852 AP Heiloo",
        address3="Noord-Holland",
        kvk="92695345",
        btw="NL866143361B01",
    )
    db.session.add(otera)
    db.session.commit()
    return otera

def seed_data():
    if Customer.query.count() > 0:
        return

    otera = get_or_create_otera()
    seed = [
        ("2026-003", "2026-06-18", "2026-07-02", "paid", [
            ("Sale - N Buurman", 3991.00),
            ("Sale - Kevin Dinkelberg", 890.00),
        ]),
        ("2026-005", "2026-07-08", "2026-07-22", "paid", [
            ("WF klant compleet - Orhan Katan", 300.00),
            ("WF klant compleet - Bert Miedema", 300.00),
        ]),
        ("2026-006", "2026-07-20", "2026-08-03", "paid", [
            ("WF klant compleet - JPM van der Aalst", 300.00),
        ]),
        ("2026-007", "2026-07-27", "2026-08-10", "paid", [
            ("WF klant compleet - I Bruel", 1756.00),
        ]),
        ("2026-008", "2026-07-31", "2026-08-14", "paid", [
            ("WF klant compleet - J Adamson", 300.00),
        ]),
        ("2026-009", "2026-08-04", "2026-08-18", "paid", [
            ("WF klant compleet - M Shelanski/Nieman", 300.00),
        ]),
        ("2026-010", "2026-08-12", "2026-08-26", "open", [
            ("WF klant compleet - Fauzi Kromosetiko", 300.00),
        ]),
        ("2026-011", "2026-09-02", "2026-09-16", "open", [
            ("WF klant compleet - Y van den Bosch", 1661.00),
            ("WF klant compleet - S Muis", 300.00),
            ("WF klant compleet - Ceyda Noa Polat", 300.00),
            ("WF klant compleet - J Jager", 300.00),
        ]),
        ("2026-012", "2026-09-07", "2026-09-21", "open", [
            ("WF klant compleet - Anita Cruze", 300.00),
            ("WF klant compleet - N Mehmedov", 300.00),
        ]),
    ]

    for no, inv_date, due, status, lines in seed:
        inv = Invoice(
            invoice_no=no,
            customer_id=otera.id,
            invoice_date=datetime.strptime(inv_date, "%Y-%m-%d").date(),
            due_date=datetime.strptime(due, "%Y-%m-%d").date(),
            status=status
        )
        db.session.add(inv)
        db.session.flush()
        for desc, price in lines:
            db.session.add(InvoiceLine(invoice_id=inv.id, quantity=1, description=desc, price_ex_vat=price))
    db.session.commit()

@app.before_request
def setup():
    db.create_all()
    seed_data()

@app.route("/")
def dashboard():
    invoices = Invoice.query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).all()
    customers = Customer.query.order_by(Customer.company_name.asc()).all()

    open_invoices = [i for i in invoices if i.status == "open"]
    paid_invoices = [i for i in invoices if i.status == "paid"]
    concept_invoices = [i for i in invoices if i.status == "concept"]
    overdue_invoices = [i for i in open_invoices if i.is_overdue]

    due_soon_invoices = [
        i for i in open_invoices
        if not i.is_overdue and i.days_until_due is not None and i.days_until_due <= 3
    ]

    totals = {
        "open": round(sum(i.total for i in open_invoices), 2),
        "paid": round(sum(i.total for i in paid_invoices), 2),
        "overdue": round(sum(i.total for i in overdue_invoices), 2),
        "concept": round(sum(i.total for i in concept_invoices), 2),
        "customers": len(customers),
        "all": round(sum(i.total for i in invoices), 2),
        "overdue_count": len(overdue_invoices),
        "due_soon_count": len(due_soon_invoices),
    }

    crm_notifications = []
    if overdue_invoices:
        crm_notifications.append({
            "type": "danger",
            "title": f"{len(overdue_invoices)} factuur/facturen over datum",
            "message": f"Totaal over datum: {euro(sum(i.total for i in overdue_invoices))}. Controleer deze facturen en stuur eventueel een herinnering.",
            "invoices": overdue_invoices,
        })
    if due_soon_invoices:
        crm_notifications.append({
            "type": "warning",
            "title": f"{len(due_soon_invoices)} factuur/facturen verlopen binnenkort",
            "message": "Deze facturen vervallen binnen 3 dagen.",
            "invoices": due_soon_invoices,
        })

    return render_template(
        "dashboard.html",
        invoices=invoices,
        customers=customers,
        totals=totals,
        today=date.today(),
        euro=euro,
        next_no=next_invoice_no(),
        crm_notifications=crm_notifications
    )

@app.route("/customers")
def customers():
    customers = Customer.query.order_by(Customer.company_name.asc()).all()
    return render_template("customers.html", customers=customers)

@app.route("/customers/add", methods=["POST"])
def add_customer():
    customer = Customer(
        company_name=request.form["company_name"].strip(),
        contact_name=request.form.get("contact_name", "").strip(),
        address1=request.form.get("address1", "").strip(),
        address2=request.form.get("address2", "").strip(),
        address3=request.form.get("address3", "").strip(),
        kvk=request.form.get("kvk", "").strip(),
        btw=request.form.get("btw", "").strip(),
        email=request.form.get("email", "").strip(),
        phone=request.form.get("phone", "").strip(),
    )
    db.session.add(customer)
    db.session.commit()
    flash("Klant toegevoegd.")
    return redirect(url_for("customers"))

@app.route("/customers/delete/<int:customer_id>")
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if customer.invoices:
        flash("Deze klant heeft facturen en kan niet verwijderd worden zolang er facturen aan gekoppeld zijn.")
        return redirect(url_for("customers"))
    db.session.delete(customer)
    db.session.commit()
    return redirect(url_for("customers"))

@app.route("/invoices/add", methods=["POST"])
def add_invoice():
    invoice_no = request.form.get("invoice_no", "").strip() or next_invoice_no()
    customer_id = int(request.form["customer_id"])
    invoice_date = datetime.strptime(request.form["invoice_date"], "%Y-%m-%d").date()
    due_date = invoice_date + timedelta(days=14)
    status = request.form.get("status", "open")

    inv = Invoice(
        invoice_no=invoice_no,
        customer_id=customer_id,
        invoice_date=invoice_date,
        due_date=due_date,
        status=status
    )
    db.session.add(inv)
    db.session.flush()

    descriptions = request.form.getlist("description")
    quantities = request.form.getlist("quantity")
    prices = request.form.getlist("price_ex_vat")

    for desc, qty, price in zip(descriptions, quantities, prices):
        desc = desc.strip()
        if not desc:
            continue
        q = float((qty or "1").replace(",", "."))
        p = parse_amount(price)
        if p <= 0:
            continue
        db.session.add(InvoiceLine(invoice_id=inv.id, quantity=q, description=desc, price_ex_vat=p))

    if not inv.lines:
        db.session.add(InvoiceLine(invoice_id=inv.id, quantity=1, description="Werkzaamheden", price_ex_vat=0))

    db.session.commit()
    flash("Factuur aangemaakt.")
    return redirect(url_for("dashboard"))

@app.route("/invoices/<int:invoice_id>/status/<status>")
def set_status(invoice_id, status):
    inv = Invoice.query.get_or_404(invoice_id)
    if status in ["open", "paid", "concept"]:
        inv.status = status
        db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/invoices/delete/<int:invoice_id>")
def delete_invoice(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    for line in inv.lines:
        db.session.delete(line)
    db.session.delete(inv)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/invoices/pdf/<int:invoice_id>")
def download_pdf(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    buffer = BytesIO()
    build_invoice_pdf(buffer, inv)
    buffer.seek(0)
    safe_no = inv.invoice_no.replace("/", "-").replace(" ", "_")
    return send_file(buffer, as_attachment=True, download_name=f"factuur_minds_agency_{safe_no}.pdf", mimetype="application/pdf")

@app.route("/invoices/mail/<int:invoice_id>")
def mail_text(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    text = f"""Onderwerp: Factuur {inv.invoice_no} - Minds Agency

Beste {inv.customer.company_name},

Bijgaand ontvangen jullie de factuur van Minds Agency.

Het totaalbedrag bedraagt {euro(inv.total)} incl. btw.
Graag ontvangen wij de betaling binnen 14 dagen op onderstaand rekeningnummer:

IBAN: {SELLER['iban']}
Ten name van: Minds Agency
Onder vermelding van: Factuur {inv.invoice_no}

Mochten er vragen zijn over de factuur, dan hoor ik dat graag.

Alvast bedankt.

Met vriendelijke groet,
Minds Agency"""
    return render_template("mail.html", invoice=inv, text=text)

@app.route("/manifest.json")
def manifest():
    return send_file("static/manifest.json", mimetype="application/manifest+json")

def build_invoice_pdf(buffer, inv):
    customer = inv.customer

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodyClean", fontName="Helvetica", fontSize=10.5, leading=14, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="BodyRight", fontName="Helvetica", fontSize=10.5, leading=14, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="BodyRightBold", fontName="Helvetica-Bold", fontSize=10.5, leading=14, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="BlockHeading", fontName="Helvetica-Bold", fontSize=12.5, leading=16, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="InvoiceTitle", fontName="Helvetica-Bold", fontSize=18, leading=22, alignment=TA_LEFT))

    page_w, page_h = A4
    left_margin = 18 * mm
    right_margin = 18 * mm
    story = []
    story.append(Paragraph("FACTUUR", styles["InvoiceTitle"]))
    story.append(Spacer(1, 5 * mm))

    def one_col_table(elements, width):
        t = Table([[x] for x in elements], colWidths=[width])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        return t

    seller_block = one_col_table([
        Paragraph(f"<b>{SELLER['name']}</b>", styles["BodyClean"]),
        Paragraph(f"KvK: {SELLER['kvk']}", styles["BodyClean"]),
        Paragraph(SELLER["address1"], styles["BodyClean"]),
        Paragraph(SELLER["address2"], styles["BodyClean"]),
    ], 78 * mm)

    details_block = one_col_table([
        Paragraph("<b>Factuurgegevens</b>", styles["BlockHeading"]),
        Paragraph(f"Factuurnummer: {inv.invoice_no}", styles["BodyClean"]),
        Paragraph(f"Factuurdatum: {inv.invoice_date.strftime('%d-%m-%Y')}", styles["BodyClean"]),
        Paragraph(f"Vervaldatum: {inv.due_date.strftime('%d-%m-%Y')}", styles["BodyClean"]),
        Paragraph("Betaaltermijn: 14 dagen", styles["BodyClean"]),
    ], 58 * mm)

    buyer_lines = [
        Paragraph("<b>Factuur aan</b>", styles["BlockHeading"]),
        Paragraph(f"<b>{customer.company_name}</b>", styles["BodyClean"]),
    ]
    if customer.contact_name:
        buyer_lines.append(Paragraph(customer.contact_name, styles["BodyClean"]))
    for field in [customer.address1, customer.address2, customer.address3]:
        if field:
            buyer_lines.append(Paragraph(field, styles["BodyClean"]))
    if customer.kvk:
        buyer_lines.append(Paragraph(f"KvK: {customer.kvk}", styles["BodyClean"]))
    if customer.btw:
        buyer_lines.append(Paragraph(f"BTW: {customer.btw}", styles["BodyClean"]))

    buyer_block = one_col_table(buyer_lines, 60 * mm)

    top_table = Table([[seller_block, details_block, buyer_block]], colWidths=[78 * mm, 58 * mm, 60 * mm])
    top_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(top_table)
    story.append(Spacer(1, 10 * mm))

    rows = [["Aantal", "Omschrijving", "Prijs excl. btw", "Totaal excl. btw"]]
    for line in inv.lines:
        qty = str(int(line.quantity)) if line.quantity == int(line.quantity) else str(line.quantity).replace(".", ",")
        rows.append([qty, Paragraph(line.description, styles["BodyClean"]), euro(line.price_ex_vat), euro(line.total_ex_vat)])

    items_table = Table(rows, colWidths=[20 * mm, 95 * mm, 35 * mm, 35 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEFF2")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, 0), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7CDD4")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 12 * mm))

    payment_block = one_col_table([
        Paragraph("<b>Betalingsgegevens</b>", styles["BlockHeading"]),
        Paragraph(f"Graag het totaalbedrag binnen 14 dagen overmaken naar IBAN {SELLER['iban']} t.n.v. {SELLER['name']}.", styles["BodyClean"]),
        Paragraph(f"Vermeld bij betaling het factuurnummer {inv.invoice_no}.", styles["BodyClean"]),
    ], 105 * mm)

    totals_table = Table([
        [Paragraph("Subtotaal:", styles["BodyClean"]), Paragraph(euro(inv.subtotal), styles["BodyRight"])],
        [Paragraph("BTW 21%:", styles["BodyClean"]), Paragraph(euro(inv.vat), styles["BodyRight"])],
        [Paragraph("<b>Totaal te betalen:</b>", styles["BodyClean"]), Paragraph(f"<b>{euro(inv.total)}</b>", styles["BodyRightBold"])],
    ], colWidths=[42 * mm, 28 * mm])
    totals_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#C7CDD4")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FB")),
        ("LINEABOVE", (0, 2), (-1, 2), 0.8, colors.HexColor("#C7CDD4")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    bottom_table = Table([[payment_block, totals_table]], colWidths=[112 * mm, 70 * mm])
    bottom_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(bottom_table)

    def footer(c, doc):
        c.saveState()
        y = 14 * mm
        c.setStrokeColor(colors.HexColor("#C7CDD4"))
        c.setLineWidth(0.7)
        c.line(left_margin, y + 6 * mm, page_w - right_margin, y + 6 * mm)
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawString(left_margin, y, f"Minds Agency - KvK {SELLER['kvk']} - IBAN {SELLER['iban']} - Betaling binnen 14 dagen")
        c.restoreState()

    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=left_margin, rightMargin=right_margin, topMargin=20*mm, bottomMargin=30*mm)
    doc.build(story, onFirstPage=footer)

if __name__ == "__main__":
    app.run(debug=True)
