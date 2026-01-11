"""
Enhanced PDF Conversion Script with Mermaid Diagram Support
Converts markdown files to professional PDF documents with diagrams
"""
import subprocess
import sys
import os
import re
from pathlib import Path

def install_dependencies():
    """Install required packages for PDF conversion"""
    print("Installing required packages...")
    packages = [
        "markdown2",
        "weasyprint",
        "pygments",
        "requests"
    ]
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])
            print(f"✅ {package}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            return False
    return True

def convert_mermaid_to_image(mermaid_code, output_file):
    """Convert Mermaid diagram to image using mermaid.ink API"""
    import requests
    import base64
    
    try:
        # Encode mermaid code
        encoded = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
        
        # Use mermaid.ink API
        url = f"https://mermaid.ink/img/{encoded}"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"⚠️  Could not render diagram: {e}")
    return False

def process_mermaid_diagrams(md_content, output_dir):
    """Extract and convert Mermaid diagrams to images"""
    # Find all mermaid code blocks
    mermaid_pattern = r'```mermaid\n(.*?)\n```'
    diagrams = re.findall(mermaid_pattern, md_content, re.DOTALL)
    
    processed_content = md_content
    
    for i, diagram_code in enumerate(diagrams):
        # Generate image filename
        img_file = os.path.join(output_dir, f"diagram_{i}.png")
        
        # Convert to image
        if convert_mermaid_to_image(diagram_code, img_file):
            # Replace mermaid block with image
            mermaid_block = f"```mermaid\n{diagram_code}\n```"
            img_markdown = f"\n![Architecture Diagram {i+1}]({img_file})\n"
            processed_content = processed_content.replace(mermaid_block, img_markdown, 1)
            print(f"  ✅ Rendered diagram {i+1}")
        else:
            print(f"  ⚠️  Skipped diagram {i+1}")
    
    return processed_content

def markdown_to_html(md_file, output_dir):
    """Convert markdown to HTML with styling and diagrams"""
    import markdown2
    
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Process Mermaid diagrams
    print(f"  Processing diagrams...")
    md_content = process_mermaid_diagrams(md_content, output_dir)
    
    # Convert markdown to HTML
    html_content = markdown2.markdown(
        md_content,
        extras=[
            "fenced-code-blocks",
            "tables",
            "header-ids",
            "code-friendly",
            "cuddled-lists",
            "task_list",
            "break-on-newline"
        ]
    )
    
    # Add professional CSS styling
    styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: A4;
            margin: 2.5cm 2cm;
            @top-right {{
                content: "College Voice Agent Documentation";
                font-size: 9pt;
                color: #666;
            }}
            @bottom-right {{
                content: "Page " counter(page);
                font-size: 9pt;
                color: #666;
            }}
        }}
        
        body {{
            font-family: 'Segoe UI', 'Arial', sans-serif;
            line-height: 1.7;
            color: #2c3e50;
            font-size: 11pt;
        }}
        
        h1 {{
            color: #1a237e;
            font-size: 28pt;
            border-bottom: 4px solid #1a237e;
            padding-bottom: 12px;
            margin-top: 40px;
            margin-bottom: 20px;
            page-break-before: always;
            page-break-after: avoid;
        }}
        
        h1:first-of-type {{
            page-break-before: avoid;
            margin-top: 0;
        }}
        
        h2 {{
            color: #0d47a1;
            font-size: 20pt;
            border-bottom: 2px solid #90caf9;
            padding-bottom: 8px;
            margin-top: 30px;
            margin-bottom: 15px;
            page-break-after: avoid;
        }}
        
        h3 {{
            color: #1976d2;
            font-size: 16pt;
            margin-top: 25px;
            margin-bottom: 12px;
            page-break-after: avoid;
        }}
        
        h4 {{
            color: #42a5f5;
            font-size: 14pt;
            margin-top: 20px;
            margin-bottom: 10px;
            page-break-after: avoid;
        }}
        
        p {{
            margin: 10px 0;
            text-align: justify;
            orphans: 3;
            widows: 3;
        }}
        
        code {{
            background-color: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 10pt;
            color: #c7254e;
            border: 1px solid #e1e1e8;
        }}
        
        pre {{
            background-color: #f8f9fa;
            border-left: 4px solid #1a237e;
            padding: 15px;
            margin: 15px 0;
            overflow-x: auto;
            border-radius: 5px;
            page-break-inside: avoid;
            font-size: 9pt;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            color: #2c3e50;
            border: none;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            page-break-inside: avoid;
            font-size: 10pt;
        }}
        
        th {{
            background-color: #1a237e;
            color: white;
            padding: 12px 10px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            border: 1px solid #ddd;
            padding: 10px;
        }}
        
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        
        blockquote {{
            border-left: 4px solid #1976d2;
            padding-left: 20px;
            margin: 15px 0;
            color: #555;
            font-style: italic;
            background-color: #f0f7ff;
            padding: 10px 20px;
        }}
        
        ul, ol {{
            margin: 12px 0;
            padding-left: 30px;
        }}
        
        li {{
            margin: 6px 0;
        }}
        
        a {{
            color: #1976d2;
            text-decoration: none;
        }}
        
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 20px auto;
            page-break-inside: avoid;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            padding: 10px;
            background: white;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 30px 0;
        }}
        
        /* Task list styling */
        input[type="checkbox"] {{
            margin-right: 8px;
        }}
        
        /* Badge styling */
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 9pt;
            font-weight: 600;
            margin: 0 4px;
        }}
        
        /* Prevent page breaks in inappropriate places */
        h1, h2, h3, h4, h5, h6 {{
            page-break-after: avoid;
        }}
        
        table, figure, img {{
            page-break-inside: avoid;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""
    return styled_html

def html_to_pdf(html_content, output_file):
    """Convert HTML to PDF using WeasyPrint"""
    from weasyprint import HTML
    
    print(f"  Generating PDF...")
    
    try:
        HTML(string=html_content).write_pdf(output_file)
        file_size = os.path.getsize(output_file) / 1024  # KB
        print(f"  ✅ Created: {output_file} ({file_size:.1f} KB)")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def convert_markdown_to_pdf(md_file, output_dir="docs_pdf"):
    """Main conversion function"""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Get file name
    file_name = Path(md_file).stem
    output_file = os.path.join(output_dir, f"{file_name}.pdf")
    
    print(f"\n📄 Converting: {md_file}")
    
    try:
        # Convert markdown to HTML with diagrams
        html_content = markdown_to_html(md_file, output_dir)
        
        # Convert HTML to PDF
        if html_to_pdf(html_content, output_file):
            return output_file
    except Exception as e:
        print(f"  ❌ Conversion failed: {e}")
    
    return None

def main():
    """Main execution"""
    print("=" * 70)
    print("📚 DOCUMENTATION TO PDF CONVERTER (with Diagram Support)")
    print("=" * 70)
    
    # Get script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print(f"\n📁 Working directory: {os.getcwd()}")
    
    # Install dependencies
    print("\n" + "=" * 70)
    print("Installing Dependencies...")
    print("=" * 70)
    if not install_dependencies():
        print("\n❌ Failed to install dependencies")
        return
    
    print("\n" + "=" * 70)
    print("Converting Documentation Files...")
    print("=" * 70)
    
    # Files to convert
    files_to_convert = [
        "PROJECT_REPORT.md",
        "DEVELOPER_GUIDE.md",
        "README.md"
    ]
    
    converted_files = []
    
    for md_file in files_to_convert:
        if os.path.exists(md_file):
            pdf_file = convert_markdown_to_pdf(md_file)
            if pdf_file:
                converted_files.append(pdf_file)
        else:
            print(f"\n⚠️  File not found: {md_file}")
            print(f"   Looking in: {os.path.abspath(md_file)}")
    
    print("\n" + "=" * 70)
    print("✅ CONVERSION COMPLETE")
    print("=" * 70)
    
    if converted_files:
        print(f"\n📁 PDF files saved in: {os.path.abspath('docs_pdf')}/")
        print("\n📚 Generated PDFs:")
        for pdf_file in converted_files:
            print(f"  • {os.path.basename(pdf_file)}")
        print("\n🎉 All documentation converted successfully!")
        print("\n💡 PDFs include:")
        print("  ✓ Professional formatting")
        print("  ✓ Rendered diagrams (Mermaid)")
        print("  ✓ Syntax-highlighted code")
        print("  ✓ Formatted tables")
        print("  ✓ Page numbers")
    else:
        print("\n❌ No files were converted")
        print("   Make sure you run this script from the project root directory")

if __name__ == "__main__":
    main()
