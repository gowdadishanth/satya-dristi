Design and build a complete, high-fidelity responsive web application called “SatQuery AI”.

SatQuery AI is an agentic vision-language assistant for multimodal remote-sensing image analysis. It allows users to upload satellite imagery and ask natural-language questions. The system automatically determines the required analysis, validates the input, routes the task to specialist remote-sensing AI models, combines their outputs, and presents evidence-grounded results with confidence information and an auditable execution trace.

This is a serious Space Technology / geospatial intelligence product intended for technical users, government officers, analysts, planners, disaster-management teams, agriculture teams, and researchers.

IMPORTANT:
This must NOT look like a generic AI SaaS landing page or a “vibe coded” AI website.
It should look like a credible professional geospatial intelligence platform used for satellite analysis.

==================================================
1. PRODUCT EXPERIENCE
==================================================

Create a complete application experience, not only a landing page.

Primary product flow:

Upload satellite image(s)
→ validate compatibility
→ enter natural-language query
→ classify requested task
→ agent selects specialist tools
→ process imagery
→ generate evidence-grounded result
→ show visual evidence
→ show confidence
→ show execution trace
→ allow report export

Support these input scenarios:

1. Single image
- Optical / multispectral image
- SAR image

2. Cross-modal pair
- Optical + SAR of the same geographic area

3. Bi-temporal pair
- Before + after images
- Used for change analysis

Supported imagery formats:
- GeoTIFF
- TIFF
- PNG/JPEG for supported benchmark demonstrations

==================================================
2. BRAND / VISUAL DIRECTION
==================================================

Product name:
SatQuery AI

Positioning:
“Interactive multimodal satellite intelligence”

Do NOT use vague AI marketing language such as:
“Unlock the power of AI”
“Revolutionizing the future”
“Next-generation intelligence”
“Smarter insights”
or similar empty hero copy.

Use precise product language instead.

Suggested hero:
“Ask questions. Analyze satellite imagery.”
Supporting text:
“SatQuery AI routes remote-sensing queries to specialized vision models and returns evidence-grounded answers across optical, SAR, and temporal imagery.”

Visual tone:
- Scientific
- Technical
- Spatial
- Calm
- Precise
- Professional
- Government / research grade
- High information density without clutter

The visual language should feel closer to:
- geospatial analytics software
- mission-control interfaces
- professional GIS software
- scientific visualization
- modern enterprise analytics

Avoid looking like:
- consumer social media
- crypto dashboard
- generic startup SaaS
- AI chatbot template
- gaming UI

==================================================
3. DESIGN SYSTEM
==================================================

Prioritize visual hierarchy aggressively.

Use a restrained color system:

PRIMARY:
Deep space/navy blue

SECONDARY:
A controlled satellite/teal or cyan accent

NEUTRALS:
White
Off-white
Very light gray
Medium gray
Dark charcoal

Use status colors only when semantically necessary:
- Green = verified / successful
- Amber = warning / uncertainty
- Red = error / incompatible input

Do NOT use excessive colors.

Do NOT create rainbow interfaces.

Do NOT use purple gradients.

Do NOT use gradient-heavy backgrounds.

Do NOT use excessive glass effects everywhere.

==================================================
4. THEMING SYSTEM
==================================================

Create a Settings page containing a visual theme selector.

Users must be able to switch between three interface themes:

1. NeoMorphism
2. GlassMorphism
3. Bento Grid UI

All three themes should preserve the exact same information architecture, functionality, content hierarchy, and component system.

Only the visual treatment changes.

NeoMorphism:
- subtle raised surfaces
- restrained shadows
- tactile controls
- soft neutral surfaces
- minimal depth

GlassMorphism:
- controlled translucent surfaces
- restrained blur
- thin borders
- subtle transparency
- NO excessive glowing gradients

Bento Grid:
- structured modular cards
- asymmetric but disciplined layout
- strong information grouping
- clear content hierarchy
- compact analytical dashboard aesthetic

The default theme should be the most professional and practical theme for a scientific/government application.

Theme switching must feel like a real application feature, not a decorative toggle.

Persist selected theme visually throughout all pages.

==================================================
5. TYPOGRAPHY
==================================================

Use one consistent modern sans-serif typeface throughout the entire product.

Create a clear type scale:

Display / hero
Page title
Section heading
Card heading
Body
Secondary text
Metadata
Labels

Use typography primarily for hierarchy rather than decorative styling.

Avoid:
- excessive bold text
- random font sizes
- mixing multiple font families
- oversized marketing typography

Text must remain highly readable at a glance.

==================================================
6. LAYOUT PRINCIPLES
==================================================

Follow these principles throughout the entire application:

1. Prioritize hierarchy.
2. Design for easy scanning.
3. Make important information findable within seconds.
4. Use whitespace intentionally.
5. Use grouping to distinguish related information.
6. Avoid visual clutter.
7. Keep controls predictable.
8. Maintain consistent spacing.
9. Use repeated components consistently.
10. Use the Gestalt principles of proximity, similarity, continuity, common region, figure-ground, and common fate where appropriate.

Whitespace is an intentional structural element.
Do not fill empty space just because it exists.

Use a consistent spacing system.

Prefer:
- clear sections
- cards with meaningful grouping
- strong alignment
- clean grids
- predictable navigation

Avoid:
- excessive floating elements
- random cards
- unnecessary decorative shapes
- visual noise

==================================================
7. STRICT “NOT VIBE-CODED” RULES
==================================================

Never use:

- Purple gradients
- Huge gradient blobs
- Pill-shaped buttons everywhere
- Overly rounded UI
- Fake user reviews
- Fake customer testimonials
- Fake metrics
- Fake counters
- Fake “trusted by” logos
- Fake activity numbers
- Fake urgency
- Emoji icons
- Generic AI sparkle icons
- AI-generated imagery
- AI-generated marketing copy
- “Made with AI” badges
- “Powered by magic” type language
- Cursor-following animations
- Fake typing animations
- Excessive scroll animations
- Excessive parallax
- Floating decorative blobs
- Endless dashboard animations
- Random glowing borders
- Excessive gradients
- Unnecessary 3D illustrations
- Stock-photo style hero imagery
- Generic robot illustrations
- ChatGPT clone styling

DO NOT add fake data solely to make the application look impressive.

Where data is shown, make it clearly demonstrative/sample data or use realistic analytical examples.

==================================================
8. NAVIGATION
==================================================

Create a persistent professional application navigation.

Desktop navigation:

SatQuery AI logo
Dashboard
Analyze
History
Reports
Settings

Right side:
System status
User profile

Sidebar navigation is acceptable for the analytical application interface.

Navigation should be compact and functional.

Do not use oversized navigation.

==================================================
9. LANDING PAGE
==================================================

Create a clean professional landing page introducing the platform.

Hero section:

Eyebrow:
“MULTIMODAL REMOTE-SENSING INTELLIGENCE”

Heading:
“Ask questions. Analyze satellite imagery.”

Subheading:
“Analyze optical, SAR, and temporal satellite imagery using natural-language queries and domain-adapted vision models.”

Primary CTA:
“Open Analysis Workspace”

Secondary CTA:
“View How It Works”

Hero visual should be an actual product interface preview, not a decorative AI illustration.

Show a satellite analysis workspace preview containing:
- satellite imagery
- query input
- analysis result
- confidence
- evidence
- execution trace

Below hero:

Section:
“One workspace for multiple remote-sensing tasks”

Show four concise capability cards:

Single-Image VQA
Ask questions about a satellite image.

Grounding & Classification
Locate and identify regions described by text.

Bi-Temporal Change Analysis
Compare imagery across two dates.

Optical + SAR Analysis
Combine complementary information from both modalities.

Next section:
“How SatQuery AI works”

Show the actual pipeline:

1. Multimodal ingestion
2. Input compatibility check
3. Agentic query interpretation
4. Specialist tool selection
5. Model processing
6. Evidence fusion
7. Confidence estimation
8. Auditable output

Use a clean horizontal process diagram.

Next section:
“Built for evidence-grounded analysis”

Show:
Visual evidence
Confidence score
Execution trace
Downloadable report

Next section:
“Designed for real remote-sensing workflows”

Use realistic application areas:
Agriculture
Disaster management
Urban planning
Forest monitoring
Water-resource assessment
Infrastructure analysis
Environmental monitoring

Do not invent statistics or fake customer logos.

Footer should include:
Product
Documentation
Privacy Policy
Terms & Conditions
Contact
Favicon / brand mark

==================================================
10. MAIN DASHBOARD
==================================================

Create a professional analytical dashboard.

Header:
“Analysis Workspace”

Secondary status:
“System ready”

Main layout:

LEFT:
Input / query workspace

CENTER:
Image analysis canvas

RIGHT:
Analysis context / execution status

Top area:
New Analysis
Recent Analyses
Saved Reports

Input section:

“Upload imagery”

Allow:
Single Image
Optical + SAR
Before + After

Drag-and-drop upload component.

Show:
File name
Format
Resolution
Sensor
Timestamp
Coordinate reference information
Compatibility status

Use clear validation states.

Example:

OPTICAL
Cartosat-style optical image
Compatible

SAR
RISAT-style SAR image
Compatible

Do not imply actual sensor metadata exists unless it is provided.

==================================================
11. QUERY INTERFACE
==================================================

Create a prominent natural-language query composer.

Label:
“What do you want to know?”

Example queries:

“Describe the major land-cover types visible in this image.”

“What changed between these two dates?”

“Has the built-up area increased?”

“Use the optical and SAR images together to identify built-up and water-covered regions.”

“Highlight the water body referred to in the query.”

Query input should feel like a serious analysis tool, not a chatbot.

Provide:
Run Analysis

Optional:
Clear
Save Query

==================================================
12. AGENTIC ANALYSIS STATE
==================================================

After the user starts an analysis, show a structured execution panel.

Title:
“Analysis Pipeline”

Stages:

1. Query interpretation
2. Input validation
3. Task selection
4. Specialist tool routing
5. Model inference
6. Evidence fusion
7. Confidence estimation
8. Result generation

Display each stage with:
- status
- duration
- tool/model name when appropriate

Example:

Query interpretation
Completed

Task:
Bi-temporal change analysis

Selected tools:
Change understanding model
Grounding model

Do not expose hidden chain-of-thought.

Only show the observable execution trace and relevant execution metadata.

==================================================
13. ANALYSIS RESULT PAGE
==================================================

Create a high-quality results workspace.

Top:

Analysis Result

Show:
Task type
Input type
Date/time
Overall confidence

Main content:

LEFT:
Large satellite image / visualization canvas

CENTER:
Evidence visualization

RIGHT:
Answer panel

Answer panel:

“Answer”

Example:
“Built-up area increased primarily along the eastern corridor.”

Clearly distinguish:
Observed evidence
Model interpretation
Confidence
Uncertainty

Do not fabricate numerical results unless clearly labeled as example/demo data.

==================================================
14. VISUAL EVIDENCE
==================================================

Create a dedicated “Evidence” section.

Depending on task, support:

Original optical image
SAR image
Before image
After image
Change heatmap
Segmentation mask
Grounding bounding boxes
Highlighted regions
Comparison view

Add a layer control.

Example:

Layers:
Optical
SAR
Change map
Grounding
Segmentation
Annotations

Provide:
Show / hide
Opacity control
Zoom
Pan
Reset view

The visual evidence should be the most prominent part of analytical results.

==================================================
15. CHANGE DETECTION INTERFACE
==================================================

Create a dedicated bi-temporal analysis view.

Two synchronized image panels:

BEFORE
Date

AFTER
Date

Below or overlay:
Change visualization

Use a restrained analytical legend:

Loss
Gain
New water
Unchanged

Add:
Swipe comparison
Side-by-side comparison
Change heatmap

Show a concise change summary.

Example:
“Detected changes are concentrated along the eastern corridor.”

==================================================
16. OPTICAL + SAR ANALYSIS
==================================================

Create a dedicated cross-modal analysis presentation.

Two image panels:

OPTICAL
Spectral/context information

SAR
Structural information

Then:

FUSED ANALYSIS

Visualize the combined interpretation.

Show a small explanatory panel:

“Why both modalities matter”

Optical contributes spectral/contextual information.
SAR contributes structural information and remains useful under cloud cover.

Keep this factual and concise.

==================================================
17. GROUNDING / REGION ANALYSIS
==================================================

When the task involves text-guided grounding:

Show:
Original image
Bounding boxes / highlighted regions

Right panel:
Query
Detected region
Confidence

Example query:
“Highlight the water body referred to in the query.”

Use visually precise overlays.

Do not create cartoon-like annotations.

==================================================
18. CONFIDENCE SYSTEM
==================================================

Confidence must NOT look like a generic AI percentage badge.

Create a professional confidence component.

Example:

Confidence
High

Agreement:
Optical ✓
SAR ✓
Fusion ✓

or

Confidence
Moderate

Agreement:
Optical ✓
SAR △
Fusion ✓

When evidence disagrees, show uncertainty clearly.

Include explanatory microcopy:

“Confidence is derived from agreement between available specialist predictions.”

This reflects the product architecture and should not look like a random black-box confidence meter.

==================================================
19. EXECUTION TRACE
==================================================

Create a collapsible “Execution Trace” panel.

Show structured machine-readable information such as:

Task:
Change Analysis

Input:
Bi-temporal image pair

Models / Tools:
Change Understanding
Grounding

Parameters:
Allowed task parameters

Outputs:
Change description
Evidence map

Confidence:
Moderate

Timestamp:
Example timestamp

Do NOT display internal model chain-of-thought.

The execution trace should communicate auditability and transparency.

==================================================
20. REPORTS
==================================================

Create a Reports page.

Users can download analysis reports.

Each report row/card should show:

Analysis name
Task
Input type
Created date
Confidence
Status

Actions:
View
Download
Delete

Report detail should contain:

Executive result
Input summary
Visual evidence
Confidence
Execution trace
Relevant model/tool information
Analysis metadata

Use a professional report-preview layout.

==================================================
21. HISTORY
==================================================

Create an Analysis History page.

Include:
Search
Filters
Task type
Input type
Date
Confidence

List previous analyses.

Each row should clearly show:
Query
Task
Date
Result status
Confidence
Open result

Design it for fast scanning.

==================================================
22. SETTINGS
==================================================

Create a complete Settings page.

Sections:

Appearance
Analysis Preferences
System
Privacy
About

Appearance must contain:

Theme

[ NeoMorphism ]
[ GlassMorphism ]
[ Bento Grid UI ]

Include live visual previews of each theme.

Additional settings:

Compact / Comfortable density

Light / Dark / System appearance

However, maintain the primary three visual design modes as the main feature.

==================================================
23. PRIVACY POLICY
==================================================

Create a dedicated Privacy Policy page.

Use professional legal-document styling.

Include sections such as:

Information collected
Uploaded imagery
Query information
Usage information
Data processing
Data retention
Security
Third-party services
User rights
Contact

Do NOT invent specific legal guarantees or certifications.

Use clearly structured placeholders where actual organization-specific legal wording is required.

==================================================
24. TERMS & CONDITIONS
==================================================

Create a dedicated Terms & Conditions page.

Include sections:

Acceptance of terms
Platform usage
Uploaded data
AI-generated analysis
Accuracy and uncertainty
Acceptable use
Intellectual property
Service availability
Limitation of liability
Changes to terms
Contact

Do not make unsupported legal claims.

==================================================
25. FAVICON / BRAND IDENTITY
==================================================

Create a simple SatQuery AI favicon / app icon.

Concept:
A minimal satellite / orbital-eye / signal interpretation symbol.

It must remain recognizable at very small sizes.

Do not use a generic AI brain icon.

Do not use an emoji.

Create a clean wordmark:
SatQuery AI

Optional short descriptor:
Multimodal Remote-Sensing Intelligence

==================================================
26. ICONOGRAPHY
==================================================

Use one consistent professional icon family.

Icons should be:
- minimal
- line-based
- technical
- consistent stroke weight

Use icons for:
Upload
Satellite
Optical
SAR
Change detection
Grounding
Reports
Settings
History
System status
Download
Layers
Evidence
Execution trace

Do NOT use emoji icons.

Do NOT mix multiple unrelated icon styles.

==================================================
27. COMPONENT SYSTEM
==================================================

Create reusable components and variants.

Components should include:

Buttons
Inputs
Text areas
Upload zones
Navigation
Cards
Tabs
Badges
Status indicators
Progress indicators
Tool selectors
Image viewer
Layer controls
Confidence component
Execution trace
Report cards
Tables
Dialogs
Toast notifications
Theme selector

Create component states:

Default
Hover
Focus
Active
Disabled
Loading
Success
Warning
Error

Keep border radius moderate.

Do NOT turn everything into pill shapes.

==================================================
28. RESPONSIVE DESIGN
==================================================

Create responsive layouts for:

Desktop
Tablet
Mobile

Desktop should prioritize the analytical workspace.

Mobile should intelligently stack:
Input
Query
Analysis status
Result
Evidence
Execution trace

Do not simply shrink the desktop UI.

Navigation should become a clean mobile navigation pattern.

==================================================
29. ACCESSIBILITY
==================================================

Ensure:

Strong contrast
Readable text
Clear focus states
Keyboard-friendly controls
Semantic hierarchy
No color-only communication
Accessible button labels
Consistent interaction patterns

Do not sacrifice readability for visual effects.

==================================================
30. MOTION
==================================================

Use animation sparingly.

Allowed:
- subtle page transitions
- progress state transitions
- upload feedback
- result loading state
- panel expansion

Avoid:
- excessive scroll-triggered animations
- parallax
- cursor-following effects
- floating elements
- bouncing cards
- unnecessary micro-interactions

The product should feel fast and functional.

==================================================
31. SAMPLE DATA / DEMONSTRATION
==================================================

Use realistic remote-sensing examples for demonstration.

Potential example imagery contexts:
- agricultural land
- urban expansion
- flood-affected areas
- water bodies
- forest regions

Do not present sample data as real operational government data.

Clearly distinguish:
Demo analysis
Example result
Sample metadata

Avoid fake metrics and fabricated claims.

==================================================
32. INFORMATION ARCHITECTURE
==================================================

Final navigation structure:

Dashboard
Analyze
History
Reports
Settings

Legal:
Privacy Policy
Terms & Conditions

Core user journey:

Dashboard
→ Analyze
→ Upload imagery
→ Enter query
→ Run analysis
→ Processing / execution trace
→ Results
→ Evidence
→ Confidence
→ Execution trace
→ Download report

==================================================
33. IMPORTANT PRODUCT PRINCIPLE
==================================================

The interface must make the user understand the answer within seconds.

Information priority should generally be:

1. What did the system find?
2. Where is the evidence?
3. How confident is the result?
4. What inputs were used?
5. Which analysis/task was performed?
6. How was it executed?
7. Can the result be exported?

Do not force the user to read long paragraphs before seeing the result.

==================================================
34. FINAL DESIGN QUALITY BAR
==================================================

The finished Figma design should look like a real product that could be presented to:

- ISRO / SAC
- government departments
- disaster management teams
- agriculture departments
- remote-sensing researchers
- GIS professionals

It should communicate:

Precision
Trust
Technical capability
Scientific analysis
Auditability
Clarity

The design must feel intentional and engineered.

Do not over-design.

Do not decorate empty space unnecessarily.

Do not make the site look like it was generated from an AI website template.

Prioritize:
Hierarchy
Scanning
Evidence
Clarity
Consistency
Whitespace
Professionalism
Usability

Create the complete design system, all major pages, responsive states, reusable components, and realistic interaction states in Figma.