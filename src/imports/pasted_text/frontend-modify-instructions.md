IMPORTANT: MODIFY THE EXISTING FRONTEND ONLY.

Do NOT redesign the entire application.

Do NOT remove existing features.

Do NOT remove existing pages.

Do NOT remove existing analysis modes.

Do NOT remove existing navigation.

Do NOT remove existing execution trace.

Do NOT remove existing confidence information.

Do NOT remove existing evidence visualization.

Do NOT remove existing history.

Do NOT remove existing reports.

Do NOT remove Settings.

Do NOT remove Privacy Policy.

Do NOT remove Terms & Conditions.

Do NOT change the existing overall visual identity unless explicitly requested below.

Preserve the current design, spacing system, color palette, typography direction, navigation, components and layouts.

Only make the following functional improvements.

==================================================
1. ANALYZE SECTION
==================================================

In the existing Analyze section there are currently:

Single Image
Before / After

buttons or mode selectors.

Keep both.

Do NOT remove them.

Improve both modes by adding a real image upload workflow.

--------------------------------------------------
SINGLE IMAGE
--------------------------------------------------

When the user selects:

Single Image

show an upload area.

Include:

Upload Image

Drag & Drop

Browse Files

Supported formats:
GeoTIFF
TIFF
PNG
JPEG

The upload component should feel integrated into the existing design.

Do NOT create a new unrelated visual style.

After upload, show:

Image preview
File name
File size
Format
Image status
Remove / Replace

Then keep the existing query input and analysis controls exactly as part of the workflow.

Flow:

Single Image
→ Upload Image
→ Preview
→ Enter Query
→ Run Analysis

Do not use placeholder success states.

The upload component must be designed to connect to the real backend API.

--------------------------------------------------
BEFORE / AFTER
--------------------------------------------------

When the user selects:

Before / After

show TWO separate upload areas.

BEFORE

Upload Image

AFTER

Upload Image

Allow:

Drag & Drop
Browse Files

Supported formats:
GeoTIFF
TIFF
PNG
JPEG

After upload show:

Before image preview
Before filename
Before metadata

After image preview
After filename
After metadata

Also include:

Replace
Remove

Then:

Run Change Analysis

Flow:

Before / After
→ Upload Before
→ Upload After
→ Preview both
→ Compatibility validation
→ Run Analysis

Do NOT populate Before and After with unrelated random images.

Use real backend-provided imagery whenever demonstration imagery is displayed.

==================================================
2. REAL SATELLITE IMAGE PREVIEWS
==================================================

Where the existing frontend currently uses random / generic imagery:

replace it with actual remote-sensing imagery supplied by the backend or bundled verified public satellite-demo assets.

Use authentic:

Sentinel-1 SAR
Sentinel-2 optical
other legitimate public remote-sensing datasets

Do not use:

stock photos
AI-generated satellite images
generic landscapes
random aerial photographs
decorative Earth renders

For Before / After examples, the two images must represent the SAME geographic region at different times.

Do not place unrelated satellite images beside each other just for aesthetics.

==================================================
3. ANALYSIS RESULT
==================================================

Preserve the existing analysis result interface.

Do NOT remove:

Answer
Evidence
Confidence
Execution Trace
Input information
Analysis information

Make the uploaded images flow through the existing result interface.

The frontend should expect actual backend responses.

Do not create fake response data.

==================================================
4. REPORT SECTION — FIX THE DOWNLOAD BUTTON
==================================================

The existing report Download button currently does not actually download anything.

Fix this.

The button must call the real backend report-download endpoint.

Expected behavior:

User clicks:

Download Report

→ backend generates/retrieves actual PDF
→ browser downloads the real PDF file
→ downloaded filename is meaningful
→ PDF opens successfully

Example filename:

TerraLens_Analysis_2026-09-17.pdf

Also support:

Download JSON

for the execution trace if that option already exists or is appropriate.

Do NOT make the button simply navigate to another page.

Do NOT use a fake download animation.

Do NOT create a zero-byte file.

Do NOT use mock report content.

==================================================
5. REAL REPORT DATA
==================================================

The downloaded report should contain the actual analysis:

Query
Input information
Analysis type
Answer
Visual evidence
Confidence
Execution trace
Model/tool information
Warnings
Timestamp

The frontend should pass the correct analysis/report ID to the backend.

==================================================
6. LOADING STATES
==================================================

Use the existing visual language for meaningful loading states.

For analysis:

Queued
Validating
Processing
Generating Evidence
Calculating Confidence
Generating Report
Completed

Do not use fake progress percentages.

Do not use fake counters.

Do not use fake “AI thinking” animations.

==================================================
7. ERROR STATES
==================================================

Add proper states for:

Invalid image
Unsupported file
Incompatible before/after pair
Incompatible optical/SAR pair
Upload failure
Analysis failure
Authentication failure
Report generation failure
Download failure

Error messages should be concise and useful.

==================================================
8. GOOGLE SIGN-IN
==================================================

Preserve the existing login UI.

Connect the Google sign-in action to Firebase Authentication.

After successful authentication:

store the authenticated Firebase session/token appropriately.

Send the Firebase ID token with protected backend requests.

Do not expose Firebase private credentials in frontend code.

Use environment variables for public Firebase configuration where required.

==================================================
9. DO NOT REMOVE EXISTING FEATURES
==================================================

This is a strict requirement.

The existing frontend features must remain intact.

Specifically preserve:

Dashboard
Analyze
Single Image
Before / After
History
Reports
Settings
Privacy Policy
Terms & Conditions
Execution Trace
Confidence
Evidence
Navigation
Theme functionality already implemented
User profile
System status
All currently existing interactions

Only improve the requested upload and report functionality.

==================================================
10. DESIGN CONSISTENCY
==================================================

Do not introduce:

purple gradients
glassmorphism
bento-grid redesign
emoji icons
AI sparkles
fake metrics
fake counters
fake reviews
pill-button overload
cursor animations
excessive animations
generic AI illustrations

Keep the existing professional visual system.

Maintain:

warm off-white background
deep slate primary
blue-grey secondary
restrained neutral palette
humanist typography
strong information hierarchy
generous whitespace
editorial / geospatial aesthetic

==================================================
11. BACKEND API INTEGRATION
==================================================

Create or update the frontend API service layer so the UI is ready for the real FastAPI backend.

The frontend must support real calls for:

Authentication
Upload
Single image analysis
Before/After analysis
Optical/SAR analysis
Analysis status
Results
Evidence
Confidence
Execution Trace
History
Reports
PDF download
JSON download

Do not hardcode analysis responses.

Do not hardcode report files.

Do not silently fall back to fake demo responses when the backend fails.

==================================================
12. FINAL CHECK
==================================================

Verify:

Single Image
→ Upload works

Before / After
→ Before upload works
→ After upload works

Report
→ Download button downloads an actual file

Google Sign In
→ authenticates through Firebase

Existing features
→ still present

Existing visual design
→ preserved

Real satellite imagery
→ used instead of random placeholder imagery

Do not make any unrelated redesign changes.