# Resume Upload Directory

## Instructions for Resume Upload

### 1. File Format
- Upload your resume in PDF format
- The file MUST be named: `resume.pdf`

### 2. How to Add Your Resume
1. Replace the sample file with your actual resume
2. Make sure it's named exactly: `resume.pdf`
3. The `.env` file should point to:
   ```
   RESUME_FILE_PATH=./resumes/resume.pdf
   ```

### 3. Resume Requirements
Your resume should include:
- **Contact Information**: Name, email, phone
- **Skills Section**: List all technical skills
- **Work Experience**: Company names, positions, dates
- **Education**: Degrees and certifications
- **Keywords**: Include relevant industry keywords for better matching

### 4. Example Resume Structure
```
John Smith
Machine Learning Engineer
john.smith@email.com | (555) 123-4567

SKILLS
- Programming: Python, Java, R, SQL
- Machine Learning: TensorFlow, PyTorch, Scikit-learn
- Tools: Docker, Kubernetes, AWS, Git

EXPERIENCE
Senior ML Engineer | Tech Company | 2022-Present
- Developed and deployed ML models...
- Improved model accuracy by 25%...

EDUCATION
MS Computer Science | University Name | 2020
```

### 5. Tips for Better Job Matching
- Use industry-standard terminology
- Include both technical and soft skills
- Quantify achievements where possible
- Keep formatting simple and clean (for better text extraction)

### Note
The application will automatically extract text from your PDF resume and use it for:
- Matching against job descriptions
- Calculating compatibility scores
- Identifying relevant skills and experience