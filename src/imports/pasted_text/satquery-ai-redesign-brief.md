IMPORTANT DESIGN REVISION:

Redesign the SatQuery AI interface using the following visual direction.

The previous design was too close to a generic AI-generated SaaS interface.

This version must feel like a real scientific / geospatial intelligence product designed by an experienced product designer.

Do not make it look “AI generated”.

==================================================
1. REMOVE GLASSMORPHISM AND BENTO GRID
==================================================

Remove Glassmorphism completely.

Remove Bento Grid UI completely.

Do NOT provide either of them as selectable themes.

The only optional visual theme should be:

1. Default — Professional Editorial / Geospatial
2. NeoMorphism — Optional alternative

The Default theme must be the primary design.

The Default design should use:
- flat surfaces
- subtle borders
- restrained shadows
- strong alignment
- generous whitespace
- clear hierarchy
- moderate corner radii
- professional data visualization
- editorial-style composition

Do not make every section into a floating card.

Do not make the entire interface look like a collection of rounded rectangles.

==================================================
2. EXACT COLOR DIRECTION
==================================================

Base the visual identity on this color palette:

Primary Deep Slate:
#313851

Secondary Blue Grey:
#C2CBD3

Warm Neutral:
#F6F3ED

Additional neutrals:
#FFFFFF
#E8E6E1
#9A9A96
#50535B

Use the deep slate as the primary structural color.

Use the blue-grey as a secondary surface / supporting interface color.

Use the warm off-white as the dominant background.

Use white sparingly for elevated surfaces.

Use darker neutral text where required.

Status colors should be used only semantically:
Green for successful/verified
Amber for warnings/uncertainty
Red for errors

Do NOT introduce additional decorative colors.

Do NOT use:
- purple
- purple gradients
- blue-purple gradients
- neon colors
- rainbow gradients
- excessive cyan
- glowing UI
- colorful AI effects

The interface should feel restrained and sophisticated.

==================================================
3. IMPORTANT: TYPOGRAPHY MUST NOT LOOK “AI”
==================================================

The typography in the previous design feels too geometric / squared / synthetic.

Replace it.

Use a more humanist, editorial sans-serif typeface.

Preferred typeface direction:
- Source Sans 3
OR
- IBM Plex Sans
OR another similarly humanist professional sans-serif.

Do not use overly geometric “startup AI” typefaces.

Avoid:
- excessively squared letterforms
- oversized futuristic typography
- monospaced typography for normal UI text
- exaggerated tracking
- overly bold headings
- giant marketing headlines

Typography should feel:
- human
- editorial
- technical
- calm
- mature
- readable

Use normal sentence casing.

Avoid excessive ALL CAPS.

Use uppercase only for tiny labels such as metadata or section categories.

Headings should have natural proportions and comfortable line height.

Body text should feel like a professional software product, not an AI landing-page template.

==================================================
4. REAL SATELLITE IMAGERY IS REQUIRED
==================================================

This is extremely important.

Do NOT use:
- random landscape photographs
- generic Earth images
- stock photographs
- AI-generated satellite imagery
- abstract map illustrations
- fake futuristic satellite graphics
- generic placeholder photos

Use actual remote-sensing / satellite imagery.

The Dashboard and Analysis Workspace must prominently use REAL satellite imagery.

Prefer authentic Earth-observation imagery from public remote-sensing datasets such as:
- Sentinel-2 optical imagery
- Sentinel-1 SAR imagery
- authentic before/after remote-sensing image pairs
- public Cartosat / RISAT demonstration imagery where legitimately available

The visual appearance must clearly resemble genuine satellite / remote-sensing data.

Do not make satellite imagery look like aerial photography.

Optical imagery should retain realistic satellite spectral/color characteristics.

SAR imagery should visibly look different from optical imagery.

==================================================
5. USE REALISTIC IMAGE PAIRING
==================================================

The “Before / After” preview must use two visually related satellite images of the SAME geographic area.

Do not place two unrelated images beside each other.

The two images should represent:
- the same geographic region
- different acquisition dates
- a believable observable change

Example contexts:
- urban expansion
- flood progression
- vegetation change
- water-body expansion
- infrastructure development

Display:

BEFORE
Acquisition date

AFTER
Acquisition date

Then provide:

CHANGE DETECTION

with a visually derived change layer.

The comparison should clearly communicate that this is temporal analysis.

==================================================
6. OPTICAL + SAR MUST LOOK AUTHENTIC
==================================================

Create a real multimodal analysis preview containing:

OPTICAL
Actual multispectral / optical satellite imagery

SAR
Actual radar imagery

FUSED VIEW
Combined analytical interpretation

The three views must appear related to the same geographic region whenever possible.

Do not use three random images.

The user should immediately understand:

Optical = visual / spectral context

SAR = structural / radar information

Fusion = combined analysis

==================================================
7. DASHBOARD SHOULD LOOK LIKE A GEOSPATIAL WORKSTATION
==================================================

The dashboard must not resemble a normal SaaS analytics dashboard.

Make the satellite image the visual centerpiece.

Structure:

Top:
Navigation + system status

Main workspace:

Large satellite analysis canvas

Side panel:
Current query
Input information
Task classification
Confidence
Evidence

Bottom / secondary area:
Execution trace
Analysis metadata
Recent analyses

The imagery should occupy significantly more visual area than decorative cards.

The user should immediately see the geographic evidence.

==================================================
8. ANALYSIS WORKSPACE
==================================================

Create a dedicated analysis interface.

Header:

Analysis Workspace

Primary area:

Large satellite imagery viewer.

Under / beside it:

“What do you want to know?”

Large natural-language query field.

Example:

“Has the built-up area increased between these two observations?”

Primary action:

Run Analysis

Keep the interface visually quiet.

Do not make the query box look like ChatGPT.

Do not use a giant glowing AI input box.

==================================================
9. IMAGE VIEWER
==================================================

The satellite viewer is the core interface.

Provide:

Zoom
Pan
Reset
Fullscreen
Layer control
Opacity
Before / After
Side-by-side
Swipe comparison

Use thin, unobtrusive controls.

Controls should look like professional GIS software.

Do not use giant floating pill controls.

Use compact rectangular or subtly rounded controls.

==================================================
10. RESULTS HIERARCHY
==================================================

The results page must prioritize information in this order:

1. Answer
2. Visual evidence
3. Confidence
4. Input information
5. Analysis type
6. Execution trace
7. Export

The user should understand the result within seconds.

Example:

ANSWER

“Built-up area increased primarily along the eastern corridor.”

Then immediately show the corresponding evidence on the satellite image.

Then:

CONFIDENCE

High

Agreement:
Optical ✓
SAR ✓
Fusion ✓

Then:

EVIDENCE

Show the exact region used to support the result.

Then:

EXECUTION TRACE

Provide the observable tool/model execution metadata.

==================================================
11. BEFORE / AFTER COMPONENT
==================================================

Make the Before / After viewer one of the strongest components of the application.

Use REAL satellite imagery.

Layout:

BEFORE                         AFTER
Satellite image                Satellite image
Date                            Date

Then:

Detected change

Use subtle analytical overlays.

Use a restrained legend.

Do not use dramatic glowing red/green heatmaps.

Avoid excessive color.

Changes can be represented through:
- subtle outline
- muted highlight
- controlled mask
- restrained annotation

==================================================
12. EVIDENCE-FIRST DESIGN
==================================================

SatQuery AI is not simply a chatbot.

The central product principle is:

THE ANSWER MUST BE CONNECTED TO VISUAL EVIDENCE.

Every major result should visually connect:

Question
↓
Analysis
↓
Evidence
↓
Answer
↓
Confidence

This relationship should be immediately understandable from the interface hierarchy.

==================================================
13. EXECUTION TRACE
==================================================

Execution Trace should look like an engineering / scientific audit panel.

Example:

TASK
Bi-temporal Change Analysis

INPUT
2 satellite images

TOOLS
Change Understanding Model
Grounding Model

STATUS
Completed

CONFIDENCE
High

Do not expose internal chain-of-thought.

Only expose observable execution information.

Keep this component compact and structured.

==================================================
14. CONFIDENCE VISUALIZATION
==================================================

Do not create a giant percentage circle.

Avoid generic AI dashboard confidence gauges.

Instead create a compact analytical confidence panel.

Example:

CONFIDENCE

High

Model agreement

OPTICAL       ✓
SAR           ✓
FUSION        ✓

Use confidence as an analytical explanation, not decorative UI.

When models disagree:

MODERATE

OPTICAL       ✓
SAR           △
FUSION        ✓

Include a concise uncertainty explanation.

==================================================
15. NAVIGATION
==================================================

Use:

SatQuery AI

Dashboard
Analyze
History
Reports
Settings

Keep the navigation quiet and professional.

No oversized logo.

No excessive decorative navigation.

==================================================
16. DASHBOARD CONTENT
==================================================

Dashboard should not be filled with meaningless statistics.

Do NOT add:

Total analyses:
12,482

Accuracy:
98.7%

Users:
4,920

Processing:
99.9%

unless actual data exists.

No fake metrics.

Instead show useful operational information:

Recent Analysis

Query
Task
Date
Status
Confidence

And a prominent:

Start New Analysis

section.

==================================================
17. VISUAL LANGUAGE
==================================================

Use a restrained combination of:

#F6F3ED
#C2CBD3
#313851

The overall appearance should resemble:

scientific publication
+ professional GIS software
+ modern editorial design
+ mission-analysis workstation

It should NOT resemble:

AI startup landing page
crypto dashboard
fintech dashboard
ChatGPT clone
template-generated SaaS
gaming interface

==================================================
18. GESTALT PRINCIPLES
==================================================

Use Gestalt principles deliberately.

PROXIMITY:
Group related metadata around the image it describes.

SIMILARITY:
Use consistent visual treatment for similar actions.

COMMON REGION:
Use boundaries only when they help organize information.

FIGURE-GROUND:
Make the satellite evidence visually dominant.

CONTINUITY:
Use alignment to guide the eye through:

Input
→ Analysis
→ Evidence
→ Result

Do not create arbitrary card grids simply to fill the page.

==================================================
19. WHITESPACE
==================================================

Whitespace is structural.

Do not fill empty areas with:
- gradients
- decorative blobs
- illustrations
- statistics
- unnecessary cards

Allow satellite imagery, typography, and analytical results to breathe.

Use generous spacing between major sections.

Use tighter spacing inside related analytical components.

==================================================
20. BUTTON DESIGN
==================================================

Do not use pill-shaped buttons everywhere.

Buttons should be:
- compact
- rectangular or subtly rounded
- clearly hierarchical

Primary button:
Run Analysis

Secondary buttons:
Upload
Export Report
View Evidence

Avoid giant CTA buttons.

Avoid excessive button variants.

==================================================
21. ICONOGRAPHY
==================================================

Use one professional icon family.

Do not use emojis.

Do not use AI sparkles.

Do not use robot icons.

Do not use decorative “intelligence” icons.

Icons should communicate actual functions:

Upload
Layers
Satellite
SAR
Optical
Change
Grounding
Reports
History
Settings
Download
Search
Zoom
Fullscreen

==================================================
22. ANIMATIONS
==================================================

Keep animation extremely restrained.

Use only meaningful transitions:

Upload processing
Analysis progress
Panel expansion
Before/after transition
Layer visibility

No:
cursor animations
mouse-following effects
floating cards
scroll-triggered spectacle
parallax
fake typing
fake counters
glowing animations

The interface should feel stable and dependable.

==================================================
23. SETTINGS
==================================================

Settings should contain:

Appearance

Default Professional
NeoMorphism

Theme preview cards must show the actual interface styling.

Do NOT include Glassmorphism.

Do NOT include Bento Grid.

Also include:

Typography density
Interface density
Light / Dark / System if supported

Privacy
Terms & Conditions
About

==================================================
24. LEGAL PAGES
==================================================

Include:

Privacy Policy
Terms & Conditions

These should be proper standalone pages.

Use readable document layouts with:
- page title
- effective date placeholder
- table of contents if appropriate
- section headings
- body text
- footer

Do not make the legal pages look like dashboards.

==================================================
25. FAVICON
==================================================

Create a simple favicon for SatQuery AI.

Concept:

A minimal orbital / satellite observation symbol.

It should work at 16×16 and 32×32 sizes.

No AI brain.
No robot.
No sparkle.
No emoji.

==================================================
26. RESPONSIVE BEHAVIOR
==================================================

Desktop:
Prioritize the satellite analysis workspace.

Tablet:
Maintain image prominence while stacking supporting panels intelligently.

Mobile:
Use:

Image
↓
Query
↓
Analysis status
↓
Answer
↓
Evidence
↓
Confidence
↓
Execution trace

Do not simply shrink desktop components.

==================================================
27. FINAL QUALITY CHECK
==================================================

Before finalizing the design, check:

Does it look like a genuine geospatial product?

Does the satellite imagery look authentic?

Are Before and After images actually related?

Is the imagery more prominent than decorative cards?

Does the typography feel human and editorial?

Are there only a few colors?

Are the three primary colors clearly dominant?

Is the user able to understand the result quickly?

Is whitespace being used intentionally?

Is the interface free from generic AI visual tropes?

Remove anything that looks decorative but does not improve understanding.

The final result should feel like a carefully designed scientific software product, not a Figma-generated AI concept.

The visual identity should be:

CALM
PRECISE
SCIENTIFIC
SPATIAL
EDITORIAL
TRUSTWORTHY
TECHNICAL

SatQuery AI should feel like software used to investigate satellite observations, not software that happens to have AI inside it.