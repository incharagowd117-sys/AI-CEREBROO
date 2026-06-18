from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os, PyPDF2, json, io
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

load_dotenv()
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

client = OpenAI(api_key=os.getenv('GROQ_API_KEY'), base_url="https://api.groq.com/openai/v1")

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    return text.strip()[:3000]

def generate_qa_with_groq(study_text, selected_marks):
    marks_str = ", ".join(map(str, selected_marks))
    prompt = f"""Generate exactly 10 Q&A pairs from this material for marks: {marks_str}

Answer lengths:
- 1-2 marks: 30-50 words
- 3-4 marks: 80-100 words
- 5-6 marks: 120-150 words
- 7-8 marks: 180-220 words
- 9-10 marks: 250-300 words

Material:
{study_text}

Return ONLY JSON:
{{"questions": [{{"marks": 5, "question": "Sample?", "answer": "Sample answer"}}]}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1500
    )
    
    response_text = response.choices[0].message.content.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1].replace("json", "").strip()
    
    return json.loads(response_text)

def create_pdf_from_qa(qa_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    story.append(Paragraph("Study Guide: Q&A by Mark Value", styles['Heading1']))
    story.append(Spacer(1, 0.3*inch))
    
    for idx, qa in enumerate(qa_data['questions'], 1):
        story.append(Paragraph(f"<b>Q{idx} ({qa['marks']} marks)</b>", styles['Heading2']))
        story.append(Paragraph(qa['question'], styles['Normal']))
        story.append(Paragraph(f"<b>Answer:</b> {qa['answer']}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    try:
        file = request.files['file']
        selected_marks = [int(m) for m in request.form.get('marks', '').split(',')]
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        print(f"[LOG] Extracting text from {file.filename}")
        study_text = extract_text_from_pdf(filepath)
        print(f"[LOG] Extracted {len(study_text)} characters")
        
        print(f"[LOG] Calling Groq API for marks: {selected_marks}")
        qa_data = generate_qa_with_groq(study_text, selected_marks)
        print(f"[LOG] Generated {len(qa_data['questions'])} questions")
        
        return jsonify({'success': True, 'questions': qa_data['questions']})
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/api/download-pdf', methods=['POST'])
def download_pdf():
    try:
        questions = request.get_json()['questions']
        pdf_buffer = create_pdf_from_qa({'questions': questions})
        return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name='study_guide.pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)