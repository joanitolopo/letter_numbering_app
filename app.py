from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import extract
from datetime import datetime, timedelta
import openpyxl
from io import BytesIO

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///numbering.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'
db = SQLAlchemy(app)

# Model Database
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sequence_number = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    officer_names = db.Column(db.String(500), nullable=False)
    activity = db.Column(db.String(200), nullable=False)
    document_number = db.Column(db.String(50), nullable=False, unique=True)

# Daftar nama pegawai

OFFICERS = []

def month_to_roman(month):
    roman_months = {
        1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
        7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
    }
    return roman_months[month]

def generate_document_number(sequence_number, date):
    year = date.strftime('%Y')
    month_roman = month_to_roman(date.month)
    sequence_str = f"{sequence_number:02d}"
    return f"800.1.11.1/{sequence_str}/UPTD PKM.B-SR/{month_roman}/{year}"

def is_sunday(date):
    return date.weekday() == 6

def get_next_sequence_number(date, used_sequences):
    year = date.year
    month = date.month
    key = (year, month)
    
    # Ambil sequence_number tertinggi dari database
    max_doc = db.session.query(Document).filter(
        extract('year', Document.date) == year,
        extract('month', Document.date) == month
    ).order_by(Document.sequence_number.desc()).first()
    
    # Tentukan sequence_number awal dari database
    current_max = max_doc.sequence_number if max_doc else 0
    
    # Perbarui dengan sequence_number yang sudah digunakan dalam transaksi
    used_max = used_sequences.get(key, 0)
    next_number = max(current_max, used_max) + 1
    
    # Simpan sequence_number baru untuk tracking dalam transaksi
    used_sequences[key] = next_number
    print(f"get_next_sequence_number for {year}-{month}: current_max={current_max}, used_max={used_max}, returning {next_number}")
    return next_number

def resequence_documents(date):
    year = date.year
    month = date.month
    docs = Document.query.filter(
        extract('year', Document.date) == year,
        extract('month', Document.date) == month
    ).order_by(Document.date.asc(), Document.sequence_number.asc()).all()
    for index, doc in enumerate(docs, start=1):
        if doc.sequence_number != index:
            old_sequence = doc.sequence_number
            doc.sequence_number = index
            doc.document_number = generate_document_number(index, doc.date)
            print(f"Resequencing ID {doc.id}: old sequence={old_sequence}, new sequence={index}, new document_number={doc.document_number}")
    db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def index():
    selected_date = None
    if request.method == 'POST':
        date_str = request.form.get('filter_date')
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                documents = Document.query.filter_by(date=selected_date).order_by(Document.sequence_number.asc()).all()
            except ValueError:
                flash('Format tanggal tidak valid!', 'error')
                documents = Document.query.order_by(Document.date.asc(), Document.sequence_number.asc()).all()
        else:
            documents = Document.query.order_by(Document.date.asc(), Document.sequence_number.asc()).all()
    else:
        documents = Document.query.order_by(Document.date.asc(), Document.sequence_number.asc()).all()
    return render_template('index.html', documents=documents, selected_date=selected_date)

@app.route('/add', methods=['GET', 'POST'])
def add_document():
    if request.method == 'POST':
        try:
            start_date_str = request.form['start_date']
            end_date_str = request.form.get('end_date')
            officer_names = []
            for i in range(1, 7):
                officer = request.form.get(f'officer_names_{i}')
                if officer and officer.strip():
                    officer_names.append(officer.strip())
            activity = request.form['activity'].strip()

            # Validasi input
            if not activity:
                flash('Kegiatan harus diisi!', 'error')
                return redirect(url_for('add_document'))

            if not officer_names:
                flash('Pilih setidaknya satu petugas!', 'error')
                return redirect(url_for('add_document'))

            if len(officer_names) > 6:
                flash('Maksimal 6 petugas per kegiatan!', 'error')
                return redirect(url_for('add_document'))

            # Validasi nama petugas
            officer_names = list(dict.fromkeys(officer_names))  # Hilangkan duplikasi
            for officer in officer_names:
                if officer not in OFFICERS:
                    flash(f'Nama petugas {officer} tidak valid!', 'error')
                    return redirect(url_for('add_document'))

            # Parse tanggal
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = start_date if not end_date_str else datetime.strptime(end_date_str, '%Y-%m-%d').date()

            # Validasi rentang tanggal
            if end_date < start_date:
                flash('Tanggal selesai harus sama atau setelah tanggal mulai!', 'error')
                return redirect(url_for('add_document'))

            # Generate daftar tanggal
            date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]

            # Dictionary untuk melacak sequence_number yang digunakan per bulan dalam transaksi
            used_sequences = {}

            # Validasi dan siapkan dokumen untuk setiap tanggal
            new_docs = []
            for date in date_range:
                # Validasi hari Minggu
                if is_sunday(date):
                    flash(f'Tidak dapat menambahkan dokumen pada hari Minggu: {date.strftime("%Y-%m-%d")}!', 'error')
                    return redirect(url_for('add_document'))

                # Validasi petugas unik per hari
                existing_docs = Document.query.filter_by(date=date).all()
                existing_officers = set()
                for doc in existing_docs:
                    existing_officers.update(doc.officer_names.split(';'))
                for officer in officer_names:
                    if officer in existing_officers:
                        flash(f'Petugas {officer} sudah terdaftar di kegiatan lain pada tanggal {date.strftime("%Y-%m-%d")}!', 'error')
                        return redirect(url_for('add_document'))

                # Validasi kegiatan unik per hari
                if Document.query.filter_by(date=date, activity=activity).first():
                    flash(f'Kegiatan "{activity}" sudah ada untuk tanggal {date.strftime("%Y-%m-%d")}!', 'error')
                    return redirect(url_for('add_document'))

                # Hitung nomor urut untuk bulan ini, dengan mempertimbangkan sequence yang sudah digunakan
                sequence_number = get_next_sequence_number(date, used_sequences)

                # Generate nomor surat
                document_number = generate_document_number(sequence_number, date)

                # Validasi nomor surat unik
                if Document.query.filter_by(document_number=document_number).first():
                    flash(f'Nomor surat {document_number} sudah digunakan untuk tanggal {date.strftime("%Y-%m-%d")}!', 'error')
                    return redirect(url_for('add_document'))

                # Siapkan dokumen baru
                new_doc = Document(
                    sequence_number=sequence_number,
                    date=date,
                    officer_names=';'.join(officer_names),
                    activity=activity,
                    document_number=document_number
                )
                new_docs.append(new_doc)
                print(f"Prepared document for {date}: sequence_number={sequence_number}, document_number={document_number}")

            # Simpan semua dokumen dalam satu transaksi
            for new_doc in new_docs:
                db.session.add(new_doc)
                print(f"Adding document: sequence_number={new_doc.sequence_number}, document_number={new_doc.document_number}")
            db.session.commit()

            for new_doc in new_docs:
                print(f"Added document: date={new_doc.date}, officer_names='{new_doc.officer_names}', document_number='{new_doc.document_number}'")

            flash(f'{len(new_docs)} dokumen berhasil ditambahkan!', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'error')
            print(f"Error: {str(e)}")
            return redirect(url_for('add_document'))

    return render_template('add.html', officers=OFFICERS)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_document(id):
    document = Document.query.get_or_404(id)
    print(f"Editing document ID {id}: officer_names='{document.officer_names}'")

    if request.method == 'POST':
        try:
            date_str = request.form['date']
            officer_names = []
            for i in range(1, 7):
                officer = request.form.get(f'officer_names_{i}')
                if officer and officer.strip():
                    officer_names.append(officer.strip())
            activity = request.form['activity'].strip()

            # Validasi input
            if not activity:
                flash('Kegiatan harus diisi!', 'error')
                return redirect(url_for('edit_document', id=id))

            if not officer_names:
                flash('Pilih setidaknya satu petugas!', 'error')
                return redirect(url_for('edit_document', id=id))

            if len(officer_names) > 6:
                flash('Maksimal 6 petugas per kegiatan!', 'error')
                return redirect(url_for('edit_document', id=id))

            # Validasi nama petugas
            officer_names = list(dict.fromkeys(officer_names))
            for officer in officer_names:
                if officer not in OFFICERS:
                    flash(f'Nama petugas {officer} tidak valid!', 'error')
                    return redirect(url_for('edit_document', id=id))

            # Parse tanggal
            date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # Validasi hari Minggu
            if is_sunday(date):
                flash('Tidak dapat mengedit dokumen untuk hari Minggu!', 'error')
                return redirect(url_for('edit_document', id=id))

            # Validasi petugas unik per hari
            existing_docs = Document.query.filter(Document.date == date, Document.id != id).all()
            existing_officers = set()
            for doc in existing_docs:
                existing_officers.update(doc.officer_names.split(';'))
            for officer in officer_names:
                if officer in existing_officers:
                    flash(f'Petugas {officer} sudah terdaftar di kegiatan lain pada tanggal tersebut!', 'error')
                    return redirect(url_for('edit_document', id=id))

            # Validasi kegiatan unik per hari
            if Document.query.filter(Document.date == date, Document.activity == activity, Document.id != id).first():
                flash('Kegiatan ini sudah ada untuk tanggal tersebut!', 'error')
                return redirect(url_for('edit_document', id=id))

            # Update data dokumen
            old_date = document.date
            document.date = date
            document.officer_names = ';'.join(officer_names)
            document.activity = activity

            # Perbarui nomor urut dan nomor surat jika bulan berubah
            if old_date.year != date.year or old_date.month != date.month:
                document.sequence_number = get_next_sequence_number(date, {})
                document.document_number = generate_document_number(document.sequence_number, date)
            elif old_date != date:
                # Hanya update nomor surat jika tanggal berubah tapi masih sama bulan
                document.document_number = generate_document_number(document.sequence_number, date)

            # Validasi nomor surat unik
            if Document.query.filter(Document.document_number == document.document_number, Document.id != id).first():
                flash(f'Nomor surat {document.document_number} sudah digunakan!', 'error')
                return redirect(url_for('edit_document', id=id))

            db.session.commit()
            print(f"Updated document ID {id}: sequence_number={document.sequence_number}, document_number={document.document_number}")

            flash('Dokumen berhasil diperbarui!', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'error')
            print(f"Error: {str(e)}")
            return redirect(url_for('edit_document', id=id))

    return render_template('edit.html', document=document, officers=OFFICERS)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_document(id):
    document = Document.query.get_or_404(id)
    try:
        print(f"Deleting document ID {id}: sequence_number={document.sequence_number}, document_number={document.document_number}")
        delete_date = document.date
        db.session.delete(document)
        db.session.commit()
        resequence_documents(delete_date)
        flash('Dokumen berhasil dihapus dan nomor urut disesuaikan!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan: {str(e)}', 'error')
        print(f"Error: {str(e)}")
    return redirect(url_for('index'))

@app.route('/download_excel')
def download_excel():
    documents = Document.query.all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Riwayat Dokumen"

    headers = ['Tanggal', 'Nomor Urut', 'Nama Petugas', 'Kegiatan', 'Nomor Surat']
    ws.append(headers)

    # Format header
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="4CAF50", end_color="4CAF50", fill_type="solid")
        cell.alignment = openpyxl.styles.Alignment(horizontal="center")

    # Tulis data
    for row, doc in enumerate(documents, start=2):
        # Format officer_names dengan bullet dan newline
        officers = doc.officer_names.split(';')
        formatted_officers = '\n'.join([f"• {officer.strip()}" for officer in officers if officer.strip()])

        ws.append([
            doc.date.strftime('%Y-%m-%d'),
            doc.sequence_number,
            formatted_officers,
            doc.activity,
            doc.document_number
        ])

        # Aktifkan wrap text untuk kolom Nama Petugas
        cell = ws.cell(row=row, column=3)
        cell.alignment = openpyxl.styles.Alignment(wrap_text=True, vertical="top")

    # Atur lebar kolom
    column_widths = {'A': 15, 'B': 10, 'C': 50, 'D': 40, 'E': 30}
    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    # Atur tinggi baris
    for row in range(2, ws.max_row + 1):
        ws.row_dimensions[row].height = 20 * len(ws.cell(row=row, column=3).value.split('\n'))

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=riwayat_dokumen.xlsx'}
    )

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)