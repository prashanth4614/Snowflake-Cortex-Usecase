# PowerPoint Generation Guide

## How to Create the Presentation

You have **two options** to generate the PowerPoint presentation:

---

## Option 1: Using Python (Recommended)

### Step 1: Install python-pptx library

```bash
pip install python-pptx
```

### Step 2: Run the script

```bash
cd "/Users/prashanthmogili/My Files/Snowflake-Cortex_Use_Case/Snowflake-Cortex-Usecase"
python create_presentation.py
```

### Step 3: Open the generated file

The script will create `Cortex_Agent_Presentation.pptx` in the current directory.

---

## Option 2: Manual Creation in PowerPoint

If you cannot install python-pptx, you can manually create the presentation using the content from:
- `PRESENTATION_CONTENT.md` - Full technical version
- `EXECUTIVE_SUMMARY_PPT.md` - Executive-friendly version

### Manual Steps:

1. Open PowerPoint
2. Create a new blank presentation
3. Follow the slide structure from the markdown files
4. Use the color scheme:
   - Primary: Snowflake Blue (#29B5E8)
   - Secondary: Dark Blue (#1E3A8A)
   - Accent: Green (#10B981)
   - Text: Dark Gray (#1F2937)

---

## What the Python Script Creates

### 6 Professional Slides:

1. **Title Slide**
   - Main title with subtitle
   - 4 key highlights in colored boxes
   - Professional layout

2. **Architecture Slide**
   - 3-tier architecture diagram
   - User Interface Layer
   - Orchestration Layer
   - Tool Execution Layer
   - Arrows showing data flow

3. **Features Slide**
   - 4 feature boxes in 2x2 grid
   - Auto Agent Creation
   - Intelligent Threading
   - Smart Query Interpretation
   - Multi-Tool Orchestration

4. **Technical Implementation Slide**
   - Split view with code flow and database coverage
   - Request flow diagram
   - List of 9 database tables
   - Technical specifications

5. **Results & Impact Slide**
   - Performance metrics (4 boxes)
   - Before/After comparison table
   - Business impact visualization

6. **ROI & Conclusion Slide**
   - Time savings highlights
   - Success factors checklist
   - Strategic advantages
   - Professional closing

---

## Features of the Generated Presentation

✅ **Professional Design**
- Snowflake brand colors
- Rounded rectangles for modern look
- Consistent fonts and spacing

✅ **Visual Elements**
- Emoji icons for quick recognition
- Color-coded sections
- Tables and comparisons
- Metric highlights

✅ **Content Rich**
- Technical details
- Business value
- ROI calculations
- Use cases

✅ **Easy to Customize**
- Edit the Python script to change content
- Modify colors, fonts, sizes
- Add/remove slides
- Adjust layout

---

## Troubleshooting

### Error: "Module 'pptx' not found"

**Solution:**
```bash
pip install python-pptx
```

Or if using Python 3:
```bash
pip3 install python-pptx
```

### Error: "Permission denied"

**Solution:**
Make sure you have write permissions in the directory:
```bash
chmod +w "/Users/prashanthmogili/My Files/Snowflake-Cortex_Use_Case/Snowflake-Cortex-Usecase"
```

### Want to customize the presentation?

Edit `create_presentation.py` and modify:
- **Colors**: Change RGB values at the top
- **Content**: Update text strings in each slide section
- **Layout**: Adjust Inches() values for positioning
- **Fonts**: Change Pt() sizes and font names

---

## Quick Start Commands

```bash
# Install library
pip install python-pptx

# Navigate to directory
cd "/Users/prashanthmogili/My Files/Snowflake-Cortex_Use_Case/Snowflake-Cortex-Usecase"

# Run script
python create_presentation.py

# Open the file
open Cortex_Agent_Presentation.pptx
```

---

## Customization Examples

### Change Title
```python
# In create_presentation.py, find:
title_frame.text = "Intelligent Sales Assistant"

# Change to:
title_frame.text = "Your Custom Title"
```

### Add a Slide
```python
# Add after slide6 creation:
slide7 = prs.slides.add_slide(prs.slide_layouts[6])
add_slide_title(slide7, "New Slide Title", DARK_BLUE)
# ... add content ...
```

### Change Colors
```python
# At the top, modify:
SNOWFLAKE_BLUE = RGBColor(41, 181, 232)  # Change RGB values
```

---

## File Output

**Generated File:** `Cortex_Agent_Presentation.pptx`

**Size:** ~100-200 KB

**Format:** Microsoft PowerPoint (.pptx)

**Compatible with:**
- Microsoft PowerPoint 2010+
- Google Slides
- Apple Keynote
- LibreOffice Impress

---

## Next Steps

1. **Generate the presentation** using the Python script
2. **Review and customize** as needed
3. **Add screenshots** of your actual application
4. **Practice your presentation** using the presenter notes
5. **Export to PDF** if needed for distribution

---

## Support

If you encounter any issues:

1. Check that python-pptx is installed: `pip list | grep python-pptx`
2. Verify Python version: `python --version` (should be 3.6+)
3. Check the error message and traceback
4. Refer to python-pptx documentation: https://python-pptx.readthedocs.io/

---

## Alternative: Use Online Tools

If you prefer not to use Python, you can also:

1. **Google Slides**: Import content from markdown
2. **Canva**: Use templates and add content
3. **PowerPoint Online**: Copy-paste from markdown files
4. **Slides.com**: HTML-based presentations

---

**Happy Presenting! 🎉**
