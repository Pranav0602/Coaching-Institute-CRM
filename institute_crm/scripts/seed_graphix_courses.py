"""
Master seed and ingestion script for Graphix Techno Services course catalog and knowledge base.
Ingests 29 industry-standard, enriched course syllabus documents into:
1. academics.models.Course
2. rag.models.KnowledgeDocument (Category: STUDY_GUIDE and COURSE_CATALOGUE)
3. rag.models.DocumentChunk (with vector embeddings via IngestionService.index_document)
Also creates a standalone markdown catalog document.
"""
from __future__ import annotations

import os
import sys
import django

# Setup django environment if run directly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'institute_crm.settings')
django.setup()

from decimal import Decimal
from django.db import transaction
from academics.models import Course, Subject
from rag.models import KnowledgeDocument, DocumentChunk
from rag.services.ingestion_service import IngestionService

COURSE_DATA = [
    # =========================================================================
    # DISCIPLINE 1: MECHANICAL CAD / CAM / CAE
    # =========================================================================
    {
        "code": "MECH-AUTOCAD",
        "title": "Mechanical AutoCAD (2D Drafting & 3D Modeling)",
        "field": "Mechanical CAD/CAM/CAE",
        "duration_months": 2,
        "total_fee": Decimal("15000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/mechanical-cadcamcae-courses/autocad-classes-pune/",
        "overview": "Master mechanical computer-aided drafting and 3D modeling using Autodesk AutoCAD. This course is specially structured for mechanical, automobile, and production engineers to create manufacturing-ready drawings adhering to ISO/ASME standards with complete GD&T callouts.",
        "prerequisites": "Diploma / Degree in Mechanical, Automobile, Production Engineering or ITI Draughtsman Mechanical.",
        "software_covered": ["Autodesk AutoCAD 2024 / 2023", "AutoCAD Mechanical Toolset"],
        "modules": [
            ("Module 1: Getting Started & Workspace Setup", [
                "Introduction to CAD, AutoCAD interface, ribbons, command prompt, status bar",
                "Coordinate systems: Absolute, Relative Rectangular, Relative Polar coordinates",
                "Drafting settings: Grid, Snap, Ortho, Polar Tracking, Object Snaps (Osnap), Object Snap Tracking",
                "Unit setup, drawing limits, template creation (.dwt) with title blocks"
            ]),
            ("Module 2: 2D Geometry & Drawing Commands", [
                "Draw tools: Line, Polyline, Circle, Arc, Rectangle, Polygon, Ellipse, Spline, Revision Cloud",
                "Advanced objects: Construction Line (Xline), Ray, Point, Donut, Region, Boundary",
                "Hatching and Gradient fills, pattern scale, angle, associative hatch, island detection"
            ]),
            ("Module 3: Precision Editing & Modification Tools", [
                "Modify tools: Move, Copy, Rotate, Scale, Stretch, Trim, Extend, Fillet, Chamfer",
                "Array features: Rectangular Array, Polar Array, Path Array, Associative editing",
                "Offset, Mirror, Explode, Join, Break, Align, Lengthen commands",
                "Grip editing, object selection methods (Window, Crossing, Fence, Lasso, Quick Select)"
            ]),
            ("Module 4: Layers, Object Properties & Standards", [
                "Layer Manager, layer creation, color coding, line types, line weights, transparency",
                "Layer states, isolation, freeze/thaw, lock/unlock, viewport layer overrides",
                "Mechanical drawing standards (ISO / ASME / BIS) for center lines, hidden lines, visible lines"
            ]),
            ("Module 5: Annotation, Dimensioning & GD&T", [
                "Text styles: Single-line text, Multiline text (Mtext), fields, spell check, text formatting",
                "Dimension styles: Linear, Aligned, Angular, Arc Length, Radius, Diameter, Jogged, Ordinate",
                "Dimensioning techniques: Baseline, Continue, Dimension spacing, Dimension break, Tolerances",
                "Geometric Dimensioning & Tolerancing (GD&T): Feature Control Frames, Datum Identifiers, Form, Orientation, Location, Runout tolerances (ASME Y14.5)"
            ]),
            ("Module 6: Reusable Content, Blocks & Attributes", [
                "Block creation (Bmake, Wblock), insertion base point, block nesting",
                "Dynamic Blocks: Parameters (Linear, Rotation, Flip, Visibility), Actions (Stretch, Move, Rotate)",
                "Block Attributes: Defining attributes, extracting attribute data to bill of materials (BOM)",
                "Design Center (ADC), Tool Palettes, Content Libraries for standard fasteners & bearings"
            ]),
            ("Module 7: Layouts, Plotting & Sheet Sets", [
                "Model Space vs Paper Space, Page Setup Manager, scale factors (1:1, 1:2, 2:1)",
                "Creating and scaling layout viewports, locking viewports, non-rectangular viewports",
                "Plot styles (CTB/STB), batch plotting, publishing to multi-page PDF, DWF export, eTransmit"
            ]),
            ("Module 8: Introduction to 3D Mechanical Modeling", [
                "3D modeling workspace, 3D navigation (ViewCube, SteeringWheels, Orbit)",
                "User Coordinate System (UCS) manipulation in 3D space",
                "3D Solid Primitives: Box, Cylinder, Cone, Sphere, Pyramid, Wedge, Torus",
                "Solids from 2D profiles: Extrude, Revolve, Sweep, Loft, Presspull",
                "Boolean Operations: Union, Subtract, Intersect, 3D Fillet, 3D Chamfer, Slice, Section Plane",
                "Generating 2D drawing views from 3D models (Base, Projected, Section, Detail views with Solview/Soldraw/ViewBase)"
            ])
        ],
        "projects": [
            "Knuckle Joint & Cotter Joint 2D Assembly Drawing with Detailed Bill of Materials",
            "Flange Coupling & Plummer Block 2D Fabrication Drawing with GD&T Callouts",
            "Spur Gear & Shaft 3D Solid Model with Orthographic Multi-View Generation"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized Course Completion Certification."
    },
    {
        "code": "MECH-CATIA-V5",
        "title": "Mechanical CATIA V5 (Part, Assembly, Surfacing & Drafting)",
        "field": "Mechanical CAD/CAM/CAE",
        "duration_months": 3,
        "total_fee": Decimal("22000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/mechanical-cadcamcae-courses/catia-classes-pune/",
        "overview": "Comprehensive mastery of Dassault Systèmes CATIA V5, the global benchmark for aerospace, automotive, and industrial equipment design. Covers parametric sketcher, solid part design, complex assembly design, generative surface modeling, and generative drafting.",
        "prerequisites": "BE/B.Tech/Diploma in Mechanical, Production, Automobile or Aerospace Engineering.",
        "software_covered": ["Dassault Systèmes CATIA V5 R20 / R21"],
        "modules": [
            ("Module 1: CATIA V5 Infrastructure & Sketcher Workbench", [
                "CATIA V5 user interface, specification tree, compass manipulation, workbench navigation",
                "Sketcher Workbench: Positioned vs Normal sketch, grid, snap, construction elements",
                "Profile Toolbar: Profile, Rectangle, Oriented Rectangle, Parallelogram, Circle, Spline, Ellipse, Axis",
                "Operation Toolbar: Corner, Chamfer, Relimitation (Trim, Break, Quick Trim, Close), Transformation (Mirror, Symmetry, Translate, Rotate, Scale, Offset)",
                "Constraint Toolbar: Dimensional & Geometrical Constraints, Auto Constraint, Animate Constraint, Sketch Analysis and diagnostic troubleshooting"
            ]),
            ("Module 2: Part Design Workbench (Core Part Modeling)", [
                "Sketch-Based Features: Pad, Multi-Pad, Pocket, Multi-Pocket, Shaft, Groove, Hole (Simple, Tapered, Counterbored, Countersunk, Counterdrilled)",
                "Complex Sketch-Based Features: Rib, Slot, Stiffener, Multi-sections Solid, Removed Multi-sections Solid",
                "Dress-Up Features: Edge Fillet, Variable Radius Fillet, Chordal Fillet, Face-Face Fillet, Tritangent Fillet, Chamfer, Draft (Basic, Reflect Line, Variable Angle), Shell, Thickness, Thread/Tap, Remove Face",
                "Transformation Features: Translation, Rotation, Symmetry, Mirror, Rectangular Pattern, Circular Pattern, User Pattern, Scaling, Affinity"
            ]),
            ("Module 3: Advanced Part Modeling & Parameterization", [
                "Boolean Operations: Body management, Assemble, Add, Remove, Intersect, Union Trim, Remove Lump",
                "Hybrid Design methodology vs Non-hybrid modeling, ordering of geometrical sets and bodies",
                "Design Tables: Excel-driven parametric configurations, Formulas, Parameters, Relations",
                "PowerCopies and Catalog creation for standard engineering components",
                "Analysis tools: Measure Between, Measure Item, Inertia & Mass properties calculation"
            ]),
            ("Module 4: Assembly Design Workbench", [
                "Assembly concepts: Top-down design vs Bottom-up design methodologies",
                "Component insertion: Existing Component, Component with Positioning, Multi-Instantiation",
                "Assembly Constraints: Coincidence, Contact, Offset, Angle, Fix, Fix Together, Flexible/Rigid Sub-assembly",
                "Space Analysis: Clash & Clearance Detection, Sectioning, Distance & Band Analysis",
                "Exploded View creation, Scene management, Enhanced Bill of Materials (BOM) generation",
                "Mechanism preparation and contextual component modeling within assemblies"
            ]),
            ("Module 5: Generative Wireframe & Surface Design (GSD)", [
                "Wireframe geometry: 3D Points, Lines, Planes, Projection, Intersection, Parallel Curves, 3D Splines, Helix, Spiral, Connect Curve",
                "Basic Surfaces: Extrude, Revolve, Sphere, Cylinder, Offset Surface",
                "Advanced Surfaces: Swept Surfaces (Explicit, Line, Circle, Conic profiles), Multi-sections Surface, Blend Surface, Fill Surface",
                "Surface Operations: Join, Healing, Trim, Split, Disassemble, Boundary, Extract, Untrim, Fillets (Shape Fillet, Edge Fillet, Variable Fillet)",
                "Surface to Solid conversion: Close Surface, Thick Surface, Sew Surface, Split with Surface"
            ]),
            ("Module 6: Generative Drafting Workbench & GD&T", [
                "Drawing sheet setup, standard sheet sizes (A0 to A4), scale factors, projection methods (1st & 3rd angle)",
                "View Generation: Front, Top, Left, Isometric, Auxiliary, Unfolded views",
                "Section Views: Offset Section, Aligned Section, Offset Section Cut, Aligned Section Cut",
                "Detail & Clipping Views: Detail View, Detail View Profile, Clipping View, Broken View, Breakout View",
                "Dimensioning, Text with Leader, Roughness & Welding symbols, Datum Features & Feature Control Frames (GD&T)",
                "Generating Bill of Materials table, Balloon callouts, Frame & Title Block automation"
            ])
        ],
        "projects": [
            "Automotive Engine Piston & Connecting Rod 3D Parametric Modeling",
            "Automotive Sheet Metal Fender / Hood Complex Class-A Surface Modeling",
            "Industrial Reduction Gearbox Complete Assembly with Clash Analysis & 2D Production Drawings"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Training Certificate."
    },
    {
        "code": "MECH-CREO",
        "title": "Mechanical PTC Creo Parametric (3.0 / 7.0 / 9.0)",
        "field": "Mechanical CAD/CAM/CAE",
        "duration_months": 2.5,
        "total_fee": Decimal("18000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/mechanical-cadcamcae-courses/mechanical-creo-3-0/",
        "overview": "Master PTC Creo Parametric (formerly Pro/ENGINEER), the industry leader in 3D feature-based parametric modeling. Learn robust solid modeling, assembly design, sheet metal design, advanced surfacing, and production detailing.",
        "prerequisites": "Diploma / Degree in Mechanical, Production, Automobile or Tool & Die Engineering.",
        "software_covered": ["PTC Creo Parametric 3.0 / 7.0 / 9.0"],
        "modules": [
            ("Module 1: Creo Architecture & Parametric Sketcher", [
                "Parametric design philosophy, parent-child relationships, model tree, regeneration engine",
                "Creo interface: Ribbon bar, Quick Access toolbar, Graphics toolbar, Message log, In-graphics display",
                "Sketcher Environment: Intent Manager, Weak vs Strong dimensions, Design Intent preservation",
                "Sketching Entities: Line, Rectangle, Circle, Arc, Ellipse, Spline, Construction geometry",
                "Editing: Trim, Divide, Corner, Mirror, Rotate & Resize, Offset, Thicken",
                "Constraints: Coincident, Collinear, Concentric, Parallel, Perpendicular, Horizontal, Vertical, Equal, Symmetry"
            ]),
            ("Module 2: Solid Part Modeling Features", [
                "Base Features: Extrude (Solid & Surface, blind, symmetric, to next, through all), Revolve (360 deg, partial angle)",
                "Advanced Sweep Features: Sweep with trajectory, Helical Sweep (springs, threads), Swept Blend",
                "Engineering Features: Hole (Linear, Radial, Diameter, Standard - ISO/UNC/UNF), Round (Constant, Variable radius, Full round), Chamfer (Corner, Edge chamfer), Shell, Rib (Profile rib, Trajectory rib), Draft (Neutral plane, Draft angle)",
                "Patterning: Dimension pattern, Direction pattern, Axis pattern, Fill pattern, Curve pattern, Table pattern, Reference pattern",
                "Model display, View manager, Cross sections, Mass properties analysis"
            ]),
            ("Module 3: Assembly Modeling & Kinematics", [
                "Top-down vs Bottom-up assembly strategies",
                "Component Assembly Constraints: Coincident, Distance, Angle, Parallel, Normal, Default, Fix",
                "Mechanism Connections: Pin joint (revolute), Slider joint (prismatic), Cylinder, Ball, Planar, Bearing joints",
                "Exploded Views: Creating exploded states, offset lines, exploded animation",
                "Interference Check: Global interference, Clearance evaluation, Clash analysis",
                "Bill of Materials (BOM) creation and Family Tables for standard part libraries"
            ]),
            ("Module 4: Surface Modeling & Freeform Design", [
                "Datum features: Datum Planes, Datum Axes, Datum Points, Datum Coordinate Systems, Datum Curves",
                "Surface Creation: Extrude surface, Revolve surface, Swept surface, Blend surface, Boundary Blend",
                "Surface Operations: Merge, Trim, Extend, Offset, Project, Transform",
                "Thicken surface, Solidify (Cut / Material addition with surface geometry)"
            ]),
            ("Module 5: Sheet Metal Design Workbench", [
                "Sheet metal terminology: K-Factor, Y-Factor, Bend Allowance, Bend Deduction",
                "Primary Walls: Planar Wall, Flat Wall, Flange Wall (I, Arc, S, Open, Closed, J, C shapes)",
                "Secondary Walls & Bends: Angular Bend, Roll Bend, Transition Bend, Relief (Rip, Rectangular, Obround)",
                "Sheet Metal Cuts, Punches, Forming Tools, Flat Pattern development and DXF export for CNC punch press"
            ]),
            ("Module 6: Production Drafting & Detailing", [
                "Drawing creation, sheet formats (.frm), multi-sheet drawings, projection symbols",
                "View Generation: General view, Projection view, Auxiliary view, Detailed view, Revolved view",
                "Section Views: Full section, Half section, Offset section, Local/Broken-out section",
                "Dimensioning: Show model annotations vs Driven dimensions, Ordinate dimensioning",
                "Geometric Tolerances, Datum Targets, Surface Finish, Weld symbols, BOM Balloons and Repeat Regions"
            ])
        ],
        "projects": [
            "Universal Joint Mechanism Assembly & Kinematic Motion Simulation",
            "Sheet Metal Electrical Enclosure with Flat Pattern & CNC Bend Table",
            "Centrifugal Pump Casing & Impeller 3D Modeling with Detailed Drawing Views"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized Course Certificate."
    },
    {
        "code": "MECH-SOLIDWORKS",
        "title": "SolidWorks Mechanical Design & Simulation",
        "field": "Mechanical CAD/CAM/CAE",
        "duration_months": 2.5,
        "total_fee": Decimal("18000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/mechanical-cadcamcae-courses/solidworks-classes-pune/",
        "overview": "Industry-focused training in Dassault Systèmes SolidWorks. Learn solid part modeling, complex assemblies, generative and interactive drafting, sheet metal fabrication design, weldments, and surface design with real-world mechanical projects.",
        "prerequisites": "Diploma / Degree in Mechanical, Automobile, Industrial, or Production Engineering.",
        "software_covered": ["SolidWorks 2022 / 2023 / 2024"],
        "modules": [
            ("Module 1: SolidWorks Essentials & 2D/3D Sketching", [
                "User Interface: CommandManager, FeatureManager Design Tree, Heads-Up View toolbar, Shortcut bars (S key)",
                "2D Sketching: Line, Rectangle (Center, Corner, 3-point), Circle, Perimeter Circle, Arc, Ellipse, Slot, Polygon, Spline",
                "Sketch Relations: Horizontal, Vertical, Collinear, Coradial, Perpendicular, Parallel, Tangent, Concentric, Equal, Symmetric",
                "Smart Dimensioning, Fully Defined sketch best practices, Sketch Evaluation and Repair Sketch",
                "3D Sketching: 3D sketch planes, Space key navigation, Tab key plane switching"
            ]),
            ("Module 2: Core Part Modeling Features", [
                "Extruded Boss/Base: Blind, Up to Vertex, Up to Surface, Offset from Surface, Up to Body, Mid Plane",
                "Extruded Cut, Revolved Boss/Base, Revolved Cut, Thin Feature extrusions",
                "Swept Boss/Base: Guide curves, Profile orientation, Follow path, Twist along path",
                "Lofted Boss/Base: Guide curves, Centerline parameters, Start/End constraints, Thin feature loft",
                "Boundary Boss/Base vs Lofted Boss/Base comparison",
                "Placed Features: Hole Wizard (Counterbore, Countersink, Hole, Tap, Pipe Tap, Slot), Fillet (Constant, Variable, Face, Full Round), Chamfer, Shell, Rib, Draft",
                "Patterning & Mirror: Linear Pattern, Circular Pattern, Curve Driven Pattern, Sketch Driven Pattern, Table Driven Pattern, Mirror Feature/Body"
            ]),
            ("Module 3: Assembly Modeling & Mechanisms", [
                "Bottom-Up vs Top-Down Assembly methodologies",
                "Standard Mates: Coincident, Parallel, Perpendicular, Tangent, Concentric, Lock, Distance, Angle",
                "Advanced Mates: Profile Center, Symmetric, Width Mate, Path Mate, Linear/Linear Coupler, Limit Distance/Angle",
                "Mechanical Mates: Cam-Follower, Gear, Rack and Pinion, Screw, Universal Joint, Hinge",
                "Interference Detection, Clearance Verification, Collision Detection, Physical Dynamics simulation",
                "Exploded Views, Explode Line Sketch, Smart Fasteners (Toolbox library integration), BOM creation"
            ]),
            ("Module 4: Production Drawings & Detailing", [
                "Drawing Sheet Setup, Standard Drawing Templates (.slddrt), Projection standards (1st & 3rd angle)",
                "Standard Views: Model View, Projected View, Auxiliary View, Section View, Aligned Section, Detail View, Broken-out Section, Break View, Crop View, Alternate Position View",
                "Model Items vs Annotations: Smart Dimension, Ordinate Dimension, Chamfer/Hole Callout",
                "Geometric Tolerances (GD&T), Datum Feature Symbols, Surface Finish, Weld Symbols",
                "Tables: Bill of Materials (Top-level, Parts only, Indented), Auto-ballooning, Hole Tables, Revision Tables"
            ]),
            ("Module 5: Sheet Metal Design & Fabrication", [
                "Sheet Metal Concepts: Bend Allowance, K-Factor, Bend Table, Relief types (Rectangular, Tear, Obround)",
                "Features: Base Flange/Tab, Edge Flange, Miter Flange, Hem, Jog, Sketched Bend, Cross Break",
                "Closed Corner, Welded Corner, Corner Relief, Forming Tools (Standard & Custom tool creation)",
                "Rip, Convert to Sheet Metal, Flatten state, Exporting Flat Pattern to 1:1 DXF/DWG for Laser Cutting"
            ]),
            ("Module 6: Weldments & Structural Frame Design", [
                "Weldment environment, 2D/3D Structural Layout sketches",
                "Structural Members: Standard profiles (ISO, ANSI Inch, DIN - C-channel, I-beam, Square tube, Angle)",
                "Corner Treatments: End Miter, End Butt 1, End Butt 2, Weld gaps",
                "Trim/Extend structural members, Gussets, End Caps, Weld Beads",
                "Cut Lists: Generating automatic Weldment Cut Lists with profile lengths, angles, and quantities"
            ]),
            ("Module 7: Surface Modeling Fundamentals", [
                "Extruded, Revolved, Swept, Lofted, Boundary Surface",
                "Offset Surface, Radiate Surface, Ruled Surface, Freeform",
                "Trim Surface (Standard & Mutual), Untrim, Knit Surface, Thicken, Cut with Surface"
            ])
        ],
        "projects": [
            "Industrial Machine Vise Assembly with Exploded View and Bill of Materials",
            "Sheet Metal Computer CPU Enclosure with Forming Tools and Flat Pattern DXF",
            "Welded Structural Pipe Rack & Industrial Staircase Frame with Cut List Table"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Course Certificate."
    },
    {
        "code": "MECH-NX-CAD",
        "title": "Siemens NX CAD 10 / 12 (Advanced CAD Modeling & Synchronous Technology)",
        "field": "Mechanical CAD/CAM/CAE",
        "duration_months": 3,
        "total_fee": Decimal("22000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/mechanical-cadcamcae-courses/mechanical-uni-graphics-nx-cad-10/",
        "overview": "Master Siemens NX CAD (formerly Unigraphics NX), widely adopted by top-tier automotive and aerospace OEMs like GM, Nissan, Rolls-Royce, and Boeing. Covers advanced direct and parametric modeling, Synchronous Technology, Freeform Surfacing, and Assemblies.",
        "prerequisites": "Degree / Diploma in Mechanical, Production, Aerospace, or Automotive Engineering.",
        "software_covered": ["Siemens NX CAD 10 / 12 / 2000 Series"],
        "modules": [
            ("Module 1: Siemens NX Interface & Direct Sketching", [
                "NX Gateway, Part Navigator, Assembly Navigator, Constraint Navigator, Roles, Resource Bar",
                "Direct Sketch Environment: Sketch on Path vs Sketch on Plane",
                "Profile, Line, Arc, Circle, Studio Spline, Fillet, Chamfer, Rectangle, Polygon, Ellipse",
                "Geometric Constraints: Inferred Constraints, Horizontal, Vertical, Tangent, Parallel, Perpendicular, Collinear, Concentric, Equal Length/Radius",
                "Dimensional Constraints: Inferred Dimension, Driving vs Reference dimensions, Auto-dimensioning control"
            ]),
            ("Module 2: Solid Feature Modeling", [
                "Design Features: Extrude (Boolean operations, Draft, Offset, Limits), Revolve, Hole (General, Drill Size, Screw Clearance, Threaded, Hole Series)",
                "Sweep Features: Swept (Guide lines, Alignment, Scaling), Variational Sweep, Tube, Swept Volume",
                "Detail Features: Edge Blend (Constant, Variable radius, Corner blend), Chamfer, Draft (From plane, From parting line), Shell, Thicken, Thread",
                "Associative Copy: Pattern Feature (Linear, Circular, Polygon, Spiral, Along curve), Mirror Feature, Mirror Body, Extract Geometry"
            ]),
            ("Module 3: Synchronous Technology (Direct Modeling)", [
                "Philosophy of Synchronous Technology: Editing non-parametric / imported STEP/IGES dumb solids",
                "Modify Commands: Move Face, Pull Face, Offset Region, Replace Face, Resize Face, Resize Blend, Resize Chamfer",
                "Detail Commands: Delete Face (with heal), Copy Face, Cut Face, Paste Face, Mirror Face, Pattern Face",
                "Reuse Commands: Group Face, Make Coplanar, Make Coaxial, Make Tangent, Make Symmetric, Make Parallel, Make Perpendicular"
            ]),
            ("Module 4: Freeform Surfacing & Studio Surface", [
                "Curve Generation: 3D Curve, Combined Projection, Intersection Curve, Section Curve, Bridge Curve, Composite Curve",
                "Surface Generation: Through Curves, Through Curve Mesh, Studio Surface, Styled Sweep, Ruled Surface, Bounded Plane",
                "Surface Operations: Trimmed Sheet, Untrim, Extend Sheet, Sew, Patch, Law Extension, Transition Feature, Swoop Feature",
                "Surface analysis: Zebra mapping, Draft analysis, Radius analysis, Section analysis"
            ]),
            ("Module 5: Assembly Modeling & Wave Technology", [
                "Top-down vs Bottom-up assembly workflows in NX",
                "Assembly Constraints: Touch Align, Concentric, Distance, Angle, Parallel, Perpendicular, Fit, Center, Bond",
                "WAVE Geometry Linker: Inter-part associative linking of curves, faces, and bodies across components",
                "Reference Sets: Model, Faceted, Empty, Custom Reference Sets for assembly performance",
                "Exploded Views, Collision Detection, Assembly Clearance Analysis, Weight & Inertia Management"
            ]),
            ("Module 6: NX Drafting & Product and Manufacturing Information (PMI)", [
                "Drafting setup, Sheet standards, Borders and Title Blocks",
                "View creation: Base View, Projected View, Detail View, Section View (Simple, Stepped, Half, Revolved), Break View",
                "Dimensions, Feature Control Frames (GD&T), Datum Reference Frames, Surface Finish, Weld symbols",
                "Part Lists (BOM) customization, Auto-Ballooning, Exporting PDF, CGM, DXF/DWG",
                "PMI (Product and Manufacturing Information): Creating 3D model-based definition (MBD) dimensions and annotations"
            ]),
            ("Module 7: NX Sheet Metal Design", [
                "NX Sheet Metal Preferences: Material thickness, Bend radius, Relief parameters",
                "Features: Tab (Base & Secondary), Flange, Contour Flange, Lofted Flange, Bend, Unbend, Rebend, Jog",
                "Corner Treatments: Closed Corner, Three Bend Corner, Miter, Break Corner",
                "Flat Pattern creation, Flat Solid export to DXF for laser cutting"
            ])
        ],
        "projects": [
            "Automotive Steering Knuckle CAD Modeling & Mass Optimization",
            "Complex Aircraft Structural Bracket using Synchronous Technology & Direct Modeling",
            "Industrial Valve Assembly with WAVE Inter-Part Associativity & 2D Production Detailing"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Course Certificate."
    },
    {
        "code": "MECH-INVENTOR",
        "title": "Autodesk Inventor Professional (3D Mechanical Design & Assemblies)",
        "field": "Mechanical CAD/CAM/CAE",
        "duration_months": 2,
        "total_fee": Decimal("16000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/mechanical-cadcamcae-courses/autodesk-inventor-classes-training-course-institute-in-pune/",
        "overview": "Master Autodesk Inventor Professional for mechanical 3D CAD design, tooling, automated design accelerators, sheet metal fabrication, and weldments. Build digital prototypes and generate automated production drawings.",
        "prerequisites": "Diploma / Degree in Mechanical or Production Engineering.",
        "software_covered": ["Autodesk Inventor Professional 2023 / 2024"],
        "modules": [
            ("Module 1: Inventor Basics & Parametric Sketching", [
                "Autodesk Inventor interface, Application Options, Projects (.ipj) setup and file organization",
                "2D Sketching: Lines, Splines, Circles, Arcs, Rectangles, Slots, Polygons, Text",
                "Constraints: Coincident, Collinear, Concentric, Fix, Parallel, Perpendicular, Horizontal, Vertical, Tangent, Smooth, Symmetric, Equal",
                "General Dimensioning, Driven dimensions, Equations and Parameters table"
            ]),
            ("Module 2: 3D Part Modeling", [
                "Sketched Features: Extrude, Revolve, Sweep, Loft, Coil (Springs), Emboss, Rib",
                "Placed Features: Hole (Drilled, Counterbore, Countersink, Threaded), Fillet, Chamfer, Shell, Decal, Thread",
                "Work Features: Work Planes, Work Axes, Work Points (Offset, Angle, Tangent)",
                "Patterning: Rectangular, Circular, Sketch Driven Pattern, Mirror Feature / Body",
                "Multi-body part modeling and deriving components"
            ]),
            ("Module 3: Sheet Metal Modeling", [
                "Sheet Metal Styles & Rules: Thickness, Material, Unfold Rules (K-factor, Bend tables)",
                "Sheet Metal Features: Face, Flange, Contour Flange, Hem, Fold, Bend, Cut, Corner Seam, Corner Round",
                "Forming Tools, Rip, Unfold/Refold, Flat Pattern generation, DXF export"
            ]),
            ("Module 4: Assembly Modeling & Design Accelerators", [
                "Placing components, Degrees of Freedom (DOF), Grounding components",
                "Assembly Constraints: Mate, Flush, Angle, Tangent, Insert (Directed, Opposed)",
                "Assembly Joints: Rigid, Rotational, Slider, Cylindrical, Planar, Ball",
                "Content Center: Placing standard hardware (Bolts, Nuts, Washers, Pins, Rivets)",
                "Design Accelerators: Bolted Connection Generator, Shaft Generator, Spur Gear Generator, Bearing Generator, V-Belt Generator",
                "Interference Analysis, Contact Solver, Drive Constraint simulation"
            ]),
            ("Module 5: Weldment Design & Frame Generator", [
                "Weldment Assembly environment: Preparation, Welds (Fillet Weld, Groove Weld, Cosmetic Weld), Machining features",
                "Frame Generator: Skeleton 3D Sketches, Inserting structural frame members (Beams, Tubes, Channels), End Treatments (Miter, Notch, Trim/Extend, Cap)"
            ]),
            ("Module 6: Production Drawings & Inventor Studio", [
                "Drawing Creation (.idw / .dwg), Sheet formats, Border and Title block customization",
                "View Types: Base View, Projected View, Auxiliary View, Section View, Detail View, Overlay View, Break View",
                "Annotations: Dimensions, Hole/Thread notes, Chamfer notes, Surface texture, GD&T Feature Control Frames, Welding symbols",
                "Parts List (BOM) customization, Auto-ballooning",
                "Presentation Files (.ipn): Exploded views, Tweaks, Camera angles, Assembly animation video creation"
            ])
        ],
        "projects": [
            "Industrial Machine Vise Assembly with Design Accelerator Bolted Connections",
            "Sheet Metal Electrical Cabinet with Flat Pattern DXF for CNC Laser Cutting",
            "Structural Frame Conveyor Stand with Automated Cut List and Weldment Callouts"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Course Certificate."
    },
    {
        "code": "MECH-HVAC",
        "title": "HVAC Design & Drafting Engineering Masterclass",
        "field": "Mechanical CAD/CAM/CAE",
        "duration_months": 2.5,
        "total_fee": Decimal("20000.00"),
        "source_url": "https://graphixtechnoservices.com/hvac-desing-course/",
        "overview": "Comprehensive training in Heating, Ventilation, and Air Conditioning (HVAC) design engineering for commercial, residential, and industrial infrastructure. Covers psychrometrics, heat load estimation (HAP), duct sizing (SMACNA), chilled water piping, and BIM modeling in Revit MEP.",
        "prerequisites": "BE/B.Tech/Diploma in Mechanical or Thermal Engineering.",
        "software_covered": ["AutoCAD HVAC", "Autodesk Revit MEP (HVAC)", "HAP (Hourly Analysis Program)", "Duct & Pipe Sizers"],
        "modules": [
            ("Module 1: HVAC Thermodynamics & Psychrometrics", [
                "Thermodynamic principles in refrigeration & air conditioning cycles",
                "Psychrometric Chart: Dry Bulb, Wet Bulb, Dew Point, Relative Humidity, Specific Humidity, Enthalpy, Sensible vs Latent heat",
                "Psychrometric Processes: Sensible Heating/Cooling, Humidification, Dehumidification, Cooling & Dehumidification, Evaporative Cooling, Air Mixing"
            ]),
            ("Module 2: Heat Load Estimation & Building Thermodynamics", [
                "Building heat gain mechanisms: Solar Radiation, Transmission through Roofs, Walls, Glass (U-Values, R-Values)",
                "Internal Heat Loads: People, Lighting, Equipment, Appliances, Diversity Factors",
                "Ventilation & Infiltration: ASHRAE 62.1 & 90.1 standards, Fresh air requirements, Air changes per hour (ACH)",
                "Software-based Heat Load Estimation using Carrier HAP (Hourly Analysis Program): Weather data input, Space modeling, System selection, Plant sizing, Output analysis"
            ]),
            ("Module 3: Air Distribution & Duct Design", [
                "Air Distribution components: Supply, Return, Exhaust ducts, Diffusers, Grilles, Dampers, Louvers",
                "Duct Sizing Methods: Equal Friction Method, Velocity Reduction Method, Static Regain Method",
                "Ductulator utilization, Aspect ratios, Friction loss per 100 feet, Velocity limits based on noise criteria (NC)",
                "SMACNA Standards for Sheet Metal Duct Construction (Gauge selection, Reinforcement, Cleats, Flanges)",
                "External Static Pressure (ESP) calculation for fan/blower selection"
            ]),
            ("Module 4: HVAC Equipment Selection & Plant Design", [
                "Air Handling Units (AHU) & Fan Coil Units (FCU): Coil selection, CFM calculation, Filter grades (HEPA, Pre-filters)",
                "Central Chilled Water Plant: Water-cooled Chillers vs Air-cooled Chillers, Cooling Towers (Induced vs Forced draft)",
                "DX Systems: Split Units, Multi-Split, Variable Refrigerant Flow (VRF / VRV) systems, Packaged Units",
                "Chilled Water Piping: Two-pipe vs Four-pipe systems, Pipe sizing, Friction head loss, Primary & Secondary pump selection"
            ]),
            ("Module 5: Specialized Ventilation & Life Safety Systems", [
                "Basement Car Park Ventilation: CO sensor-based jet fan systems vs Ducted systems",
                "Kitchen Exhaust & Ecology Units: Hood design, capture velocity, grease filters",
                "Staircase & Lift Well Pressurization systems as per National Building Code (NBC) / NFPA 92A",
                "Clean Room Design standards (ISO 14644 / US Federal Standard 209E) for hospitals and pharma"
            ]),
            ("Module 6: HVAC 2D Drafting & 3D BIM (Revit MEP)", [
                "AutoCAD HVAC 2D: Single-line and Double-line duct drafting, Equipment layout, Diffuser schedules",
                "Revit MEP HVAC 3D: Creating HVAC spaces & zones, Air terminal placement, Mechanical equipment placement, 3D Duct routing (Supply, Return, Exhaust), Duct insulation, Clash detection with architectural/structural models, Section views & Shop drawings"
            ])
        ],
        "projects": [
            "Complete Heat Load Calculation & Duct Design for a 4-Story Commercial Office Building using HAP",
            "Hospital Clean Room Operation Theater (OT) Air Handling Unit & Duct Routing Project",
            "Basement Jet Fan Ventilation & Staircase Pressurization System Design"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized HVAC Design Engineer Certificate."
    },
    {
        "code": "MECH-PIPING",
        "title": "Piping Design & Plant Engineering Masterclass",
        "field": "Mechanical CAD/CAM/CAE",
        "duration_months": 3,
        "total_fee": Decimal("22000.00"),
        "source_url": "https://graphixtechnoservices.com/piping-design-course/",
        "overview": "Comprehensive professional piping engineering program for oil & gas, petrochemical, refinery, and power plants. Covers ASME B31.3 / B31.1 piping codes, P&ID development, equipment layout, 3D plant design in AutoCAD Plant 3D, and pipe stress analysis fundamentals.",
        "prerequisites": "Degree / Diploma in Mechanical, Chemical, Petroleum, or Production Engineering.",
        "software_covered": ["AutoCAD Plant 3D", "AutoCAD P&ID", "Plant 3D Spec Editor", "CAESAR II concepts"],
        "modules": [
            ("Module 1: Process Plant Engineering & Industrial Codes", [
                "Overview of Process Plants: Refineries, Petrochemicals, Power Plants, Water Treatment",
                "International Codes & Standards: ASME B31.3 (Process Piping), ASME B31.1 (Power Piping), ASME B31.4/B31.8 (Pipeline Transportation), ASME B16.5 (Pipe Flanges), ASME B16.9 (Factory-Made Butt-welding Fittings), ASTM material specifications, API 650 (Storage Tanks), API 610 (Centrifugal Pumps)"
            ]),
            ("Module 2: Piping Components & Material Specifications", [
                "Pipes: Nominal Pipe Size (NPS), Schedule (Wall thickness), Manufacturing methods (Seamless, ERW, SAW)",
                "Pipe Fittings: Elbows (90, 45, Long Radius, Short Radius), Tees (Straight, Reducing), Reducers (Concentric, Eccentric), Caps, Stub-ends",
                "Flanges: Weld Neck, Slip-on, Blind, Socket Weld, Threaded, Lap Joint; Flange Facings (Flat Face, Raised Face, Ring Type Joint - RTJ)",
                "Valves: Gate, Globe, Ball, Butterfly, Check, Plug, Needle, Pressure Safety Valves (PSV), Control Valves",
                "Gaskets & Fasteners: Spiral Wound, Non-asbestos, Ring Gaskets, Stud Bolts and Nuts",
                "Piping Material Specifications (PMS / Pipe Specs): Class ratings (150#, 300#, 600#, 900#, 1500#), Corrosion allowance"
            ]),
            ("Module 3: P&ID (Process & Instrumentation Diagrams)", [
                "Process Flow Diagrams (PFD) to Piping & Instrumentation Diagrams (P&ID) evolution",
                "Standard Instrumentation symbols (ISA 5.1), Equipment tags, Line numbering conventions",
                "Valve symbols, Specialty items (Strainers, Steam Traps, Sight Glasses, Expansion Joints)",
                "AutoCAD P&ID toolset: Creating intelligent P&IDs, dynamic line routing, automatic tagging, and validation checks"
            ]),
            ("Module 4: Equipment Layout & Plot Plan Development", [
                "Overall Plot Plan principles: Safety distances, Firefighting access, Wind direction, Roadways",
                "Unit Plot Plan & Equipment Layout: Distillation columns, Heat Exchangers, Pumps, Compressors, Fired Heaters, Storage Tanks",
                "Pipe Rack Design: Pipe rack width, height, bent spacing, elevation levels, expansion loop locations"
            ]),
            ("Module 5: 3D Plant Design using AutoCAD Plant 3D", [
                "Plant 3D Project Manager: Project structure, drawing coordination, shared databases",
                "Spec-Driven 3D Pipe Routing: Selecting pipe specs, routing with automatic fitting insertion, branch tables",
                "3D Equipment Modeling: Creating parametric pumps, horizontal/vertical vessels, exchangers, converting AutoCAD blocks to equipment, nozzle positioning",
                "Structural Modeling: Grid systems, structural steel members, pipe racks, walkways, ladders, platforms",
                "Pipe Supports: Selecting and placing standard supports (Shoes, Guides, Stops, Hangers, U-Bolts)"
            ]),
            ("Module 6: Piping Isometrics, MTO & Stress Analysis Basics", [
                "Generating Production Isometrics: Quick ISO, Production ISO, Iso themes, PCF file export",
                "Bill of Materials (BOM) / Material Take-Off (MTO) generation from 3D model",
                "Orthographic Drawing Extraction: Plans, Sections, Elevations with annotations and dimensions",
                "Pipe Stress Analysis Fundamentals: Sustained vs Thermal vs Occasional loads, Thermal expansion calculation, Flexibility analysis, Span calculation, Placement of Anchors and Spring Hangers"
            ])
        ],
        "projects": [
            "Oil Refinery Crude Distillation Unit (CDU) Pump Station 3D Piping Layout",
            "Chemical Storage Tank Farm Piping with Truck Loading Station",
            "Automated Isometric Extraction & Material Take-Off (MTO) for Offshore Separator Module"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Piping Design Engineer Certificate."
    },

    # =========================================================================
    # DISCIPLINE 2: CIVIL CAD, ARCHITECTURE & BIM
    # =========================================================================
    {
        "code": "CIVIL-AUTOCAD",
        "title": "Civil AutoCAD (Architectural & Structural 2D Drafting)",
        "field": "Civil CAD",
        "duration_months": 2,
        "total_fee": Decimal("15000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/civil-cad-courses/95-2/",
        "overview": "Professional drafting curriculum for civil engineers, architects, and site supervisors. Learn to prepare municipal sanction drawings, architectural layouts, structural reinforcement details, and building estimates following National Building Code (NBC) standards.",
        "prerequisites": "BE/B.Tech/Diploma in Civil Engineering, Architecture, or ITI Draughtsman Civil.",
        "software_covered": ["Autodesk AutoCAD 2024 / 2023"],
        "modules": [
            ("Module 1: Civil Drafting Environment & Standards", [
                "Civil engineering coordinate systems, survey coordinates, Easting/Northing units",
                "Drawing setup: Architectural feet/inches vs Metric millimeters/meters, Scale factors",
                "AIA & NBC Layer standards: Centerline, Masonry, Concrete, Doors, Windows, Plumbing, Electrical, Text, Dimensions"
            ]),
            ("Module 2: 2D Drafting Tools for Civil Plans", [
                "Drafting walls: Offset, Trim, Extend, Fillet commands, Multiline (Mline) tools for cavity & composite walls",
                "Creating standard doors, windows, ventilators, openings, staircases, and ramps",
                "Hatch patterns for civil engineering: Concrete, Earth, Brickwork, Sand, Gravel, Tiles, Plaster"
            ]),
            ("Module 3: Architectural Floor Plans, Elevations & Sections", [
                "Residential space planning: Living room, Kitchen, Bedrooms, Toilets, Balconies, Verandahs",
                "Drafting Front, Rear, and Side Elevations from floor plans",
                "Developing Cross-Sections through staircase, toilets, and structural frames",
                "Compound wall, gate details, septic tank, and underground water tank layouts"
            ]),
            ("Module 4: Structural Detailing & Schedules", [
                "Foundation Plan: Excavation layout, Isolated footings, Combined footings, Raft details",
                "Column Grid layout, Column schedule with reinforcement callouts and tie details",
                "Plinth beam & Floor beam layouts with longitudinal & cross-sectional rebar details",
                "One-way and Two-way slab rebar detailing, Crank bars, Extra top bars, Schedule of Openings"
            ]),
            ("Module 5: Municipal Sanction Drawings & Building Bye-Laws", [
                "Rules & Regulations: Floor Space Index (FSI / FAR), Built-up Area, Carpet Area, Super Built-up Area",
                "Setback calculations: Front, Rear, Side open spaces as per road width",
                "Preparing Sanction Sheet: Key plan, Site plan, Service plan, Area statement table, Rainwater harvesting layout"
            ]),
            ("Module 6: Quantity Estimation & Sheet Presentation", [
                "Extracting measurements from AutoCAD drawings for Bill of Quantities (BOQ)",
                "Paper space layouts, Viewport scaling (1:50, 1:100, 1:200), Sheet composition",
                "Batch plotting, publishing to PDF/DWF, and client presentation drawing standards"
            ])
        ],
        "projects": [
            "G+2 Modern Residential Bungalow Complete Municipal Sanction Drawing Set",
            "Multi-Family Apartment Typical Floor Plan with Structural Rebar Detailing",
            "Commercial Retail Complex Site Plan with Parking, Landscaping, and Sectional Elevations"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Civil CAD Certificate."
    },
    {
        "code": "CIVIL-REVIT-ARCH",
        "title": "Autodesk Revit Architecture (BIM Modeling Masterclass)",
        "field": "Civil CAD",
        "duration_months": 2,
        "total_fee": Decimal("18000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/civil-cad-courses/civil-revit-architecture/",
        "overview": "Full 30-day comprehensive building information modeling (BIM) program in Autodesk Revit Architecture. Learn parametric 3D building modeling, custom family creation, materials & photorealistic rendering, construction documentation, and multi-user worksharing.",
        "prerequisites": "Diploma / Degree in Civil Engineering, Architecture, Interior Design, or Construction Management.",
        "software_covered": ["Autodesk Revit 2023 / 2024"],
        "modules": [
            ("Days 1-5: BIM Concepts, UI, Levels & Walls", [
                "Day 1: Introduction to BIM (Building Information Modeling), Revit interface, Project Browser, Properties palette",
                "Day 2: Datum Elements: Creating Levels, Level constraints, Structural Grids, Grid dimensions",
                "Day 3: Basic Walls: Wall types, Location line, Base/Top constraints, Editing wall profile",
                "Day 4: Compound Walls: Layers, Materials, Wall sweeps, Wall reveals, Wall joins",
                "Day 5: Openings: Placing Doors and Windows, modifying instance/type properties, loading families"
            ]),
            ("Days 6-10: Floors, Ceilings, Roofs & Curtain Walls", [
                "Day 6: Floors: Architectural floor boundary sketch, Slope arrow, Floor openings, Cantilever slabs",
                "Day 7: Ceilings: Automatic ceiling vs Sketch ceiling, Ceiling grids, Placing light fixtures in ceilings",
                "Day 8: Roofs by Footprint: Defining slope, Overhangs, Fascia, Gutter, Roof soffits",
                "Day 9: Roofs by Extrusion: Curved roofs, Join/Unjoin roofs, Dormer openings",
                "Day 10: Curtain Walls: Curtain wall types, Curtain grids, Mullions, Embedded curtain walls in masonry"
            ]),
            ("Days 11-15: Vertical Circulation, Rooms & Spatial Layouts", [
                "Day 11: Stairs by Component: Straight, Spiral, L-shape, U-shape, Stair landing, Riser/Tread calculations",
                "Day 12: Stairs by Sketch: Custom stair boundary, risers, and stair path",
                "Day 13: Railings & Ramps: Railing types, Baluster placement, Handrails, ADA-compliant ramps",
                "Day 14: Openings: Shaft openings for lifts & service ducts, Wall opening, Vertical opening, By-face opening",
                "Day 15: Room & Area Analysis: Placing Rooms, Room separation lines, Room tags, Color fill schemes"
            ]),
            ("Days 16-20: Parametric Families, Site & Topography", [
                "Day 16: Family Editor Basics: Reference Planes, Dimensions, Labels, Parameters (Family vs Shared)",
                "Day 17: 3D Forms in Family Editor: Extrusion, Blend, Revolve, Sweep, Swept Blend, Void forms",
                "Day 18: Custom Parametric Window / Door Family creation with materials and visibility controls",
                "Day 19: Site Modeling: Toposurface / Toposolid from points and imported DWG contour lines",
                "Day 20: Site Improvements: Building pads, Subregions, Split surface, Graded regions, Site components (trees, parking)"
            ]),
            ("Days 21-25: Schedules, Quantities, Lighting & Rendering", [
                "Day 21: Schedules & Quantities: Door schedule, Window schedule, Room finishes, Calculated parameters",
                "Day 22: Material Takeoff: Wall material takeoff, Floor finish takeoff, Cost estimation formulas",
                "Day 23: Materials & Textures: Asset browser, PBR appearance, Cut pattern, Surface pattern, Bump maps",
                "Day 24: Lighting & Cameras: Sun settings, Solar study, Interior/Exterior artificial lights, Camera views",
                "Day 25: Photorealistic Rendering: Render settings, Resolution, Cloud rendering, Exporting panoramas & Walkthroughs"
            ]),
            ("Days 26-30: Detailing, Sheets, Phasing & Collaboration", [
                "Day 26: Annotation & Detailing: Dimensions, Text, Keynotes, Detail lines, Repeating details, Detail components",
                "Day 27: Sheet Composition: Title blocks, View placement, Viewport scales, Guide grids, Sheet lists",
                "Day 28: Project Phasing & Design Options: Existing, Demolition, New Construction phases, Comparing design schemes",
                "Day 29: Worksharing: Central file creation, Local copies, Worksets, Synchronize with Central, Ownership requests",
                "Day 30: Project Audit, IFC / DWG Export, Navisworks NWC export, and Capstone Project presentation"
            ])
        ],
        "projects": [
            "Luxury Residential Villa BIM Model with Custom Parametric Families, Walkthrough, and Schedule Sheets",
            "Multi-Story Commercial Office Building with Curtain Wall Facade, Phasing, and Sun Studies",
            "Complete Construction Working Drawing Sheet Package Exported to PDF and DWG"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized Revit Architecture Certificate."
    },
    {
        "code": "CIVIL-REVIT-STRUCT",
        "title": "Autodesk Revit Structure (Structural BIM & Rebar Detailing)",
        "field": "Civil CAD",
        "duration_months": 2,
        "total_fee": Decimal("18000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/civil-cad-courses/civil-revit-structure/",
        "overview": "Specialized curriculum for structural engineers and detailers. Learn structural framing, foundation modeling, 3D reinforcement (rebar) modeling, structural steel joints, analytical model generation, and structural shop drawing creation.",
        "prerequisites": "Degree / Diploma in Civil or Structural Engineering.",
        "software_covered": ["Autodesk Revit 2024 (Structure)", "Robot Structural Analysis integration"],
        "modules": [
            ("Module 1: Structural BIM Setup & Substructures", [
                "Revit Structure interface, structural template setup, linking Architectural models",
                "Copy/Monitor tools: Monitoring levels, structural grids, and columns",
                "Foundation Modeling: Isolated footings, Wall footings, Slab foundations (Mat/Raft), Pile caps and Piles",
                "Retaining walls, Basement walls, Foundation step details"
            ]),
            ("Module 2: Structural Framing & Slabs", [
                "Structural Columns: Concrete, Steel, Timber, Composite columns, Slanted columns",
                "Structural Beams: Concrete rectangular/T-beams, Steel wide-flange beams, Channels, Angles",
                "Beam Systems: Joists, Purlins, Automatic beam systems, 3D framing layout",
                "Structural Floors: Concrete slabs on grade, Metal deck composite slabs, Slab edges, Openings"
            ]),
            ("Module 3: Structural Trusses & Steel Connections", [
                "Truss Modeling: Standard Warren, Pratt, Howe trusses, Custom structural truss profiles",
                "Bracing Systems: Vertical bracing, K-bracing, Cross-bracing (X-brace)",
                "Standard Steel Connections: Base plate connections, Beam-to-column moment & shear joints, Beam-to-beam splices, Apex joints, Stiffeners and bolts"
            ]),
            ("Module 4: 3D Rebar Modeling (Reinforced Concrete Detailing)", [
                "Rebar Settings: Rebar cover settings, Bar diameter definitions, Hook styles, Bend radiuses",
                "Rebar Placement: Shape-driven rebar vs Free-form rebar, Rebar sets (Maximum spacing, Number with spacing)",
                "Reinforcing structural elements: Footings, Columns, Beam longitudinal & shear stirrups, Slab top/bottom meshes",
                "Area Reinforcement, Path Reinforcement, Fabric Wire Mesh Reinforcement",
                "Bar Bending Schedules (BBS): Automatic rebar quantity takeoff, Shape codes, Cutting lengths"
            ]),
            ("Module 5: Analytical Modeling & Analysis Integration", [
                "Analytical Model view: Analytical nodes, analytical members, boundary conditions (Fixed, Pinned, Roller)",
                "Applying Structural Loads: Dead load, Live load, Wind load, Area/Line/Point loads, Load combinations",
                "Exporting Analytical Model to Robot Structural Analysis / ETABS for structural calculations"
            ]),
            ("Module 6: Structural Documentation & Shop Drawings", [
                "Structural plans, framing elevations, rebar placement sections, detail callouts",
                "Tagging: Beam tags, Column tags, Rebar tags, Spot elevation tags, Weld symbols",
                "Schedules: Column schedule, Beam schedule, Footing schedule, Rebar cutting list",
                "Sheet creation, Title blocks, and drawing set export"
            ])
        ],
        "projects": [
            "G+5 RCC Commercial Building Complete Structural BIM Model with Full 3D Rebar Detailing",
            "Industrial Steel Warehouse with Truss Framing, Purlins, Bracing, and Parametric Steel Connections",
            "Bar Bending Schedule (BBS) and Structural Construction Sheet Package for Multi-Bay Foundation"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Revit Structure Certificate."
    },
    {
        "code": "CIVIL-3DSMAX",
        "title": "Autodesk 3ds Max Studio for Architectural Visualization",
        "field": "Civil CAD",
        "duration_months": 2,
        "total_fee": Decimal("18000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/civil-cad-courses/3ds-max-studio/",
        "overview": "Professional 3D modeling, texturing, lighting, and photorealistic rendering curriculum using Autodesk 3ds Max with V-Ray / Arnold. Learn to transform 2D CAD plans into cinematic interior renders and exterior architectural walkthroughs.",
        "prerequisites": "Basic understanding of architectural plans or AutoCAD/Revit.",
        "software_covered": ["Autodesk 3ds Max 2024", "V-Ray 6", "Adobe Photoshop"],
        "modules": [
            ("Module 1: 3ds Max Interface & Geometric Primitives", [
                "UI navigation, Four-viewport configuration, Viewport shading modes, Unit setup (Feet/Inches vs Metric)",
                "Standard Primitives: Box, Cylinder, Sphere, Torus, Teapot, Cone, Tube, Pyramid, Plane",
                "Extended Primitives: Hedra, ChamferBox, ChamferCyl, OilTank, Capsule, Spindle, L-Ext, C-Ext",
                "Transform tools: Move, Rotate, Scale, Coordinate systems, Pivot point alignment, Grid and Snap settings"
            ]),
            ("Module 2: 2D Splines & Parametric Modifiers", [
                "2D Splines: Line, Rectangle, Circle, Ellipse, Arc, Donut, Ngon, Star, Text, Helix, Section",
                "Editable Spline: Vertex, Segment, Spline sub-objects, Fillet, Chamfer, Weld, Outline, Trim, Cross-Section",
                "Modifiers: Extrude, Lathe (360 deg rotational symmetry), Bevel, Bevel Profile, Sweep, Loft",
                "Parametric Modifiers: Bend, Taper, Twist, Noise, Shell, Slice, FFD (Free Form Deformation)"
            ]),
            ("Module 3: Editable Poly Modeling for Interiors & Exteriors", [
                "Editable Poly sub-objects: Vertex, Edge, Border, Polygon, Element",
                "Modeling tools: Extrude, Inset, Bevel, Bridge, Chamfer, Cut, Slice Plane, QuickSlice, Target Weld",
                "Architectural AEC Extended Objects: Doors (Pivot, Sliding, Bi-fold), Windows (Awning, Casement, Projected), Walls, Railings, Stairs, Foliage",
                "Importing and cleaning 2D AutoCAD floor plans for 3D extrusion"
            ]),
            ("Module 4: Materials & Shaders (Slate Material Editor & V-Ray)", [
                "Slate Material Editor interface, Multi/Sub-Object materials, PBR Material workflow",
                "V-Ray Material (VRayMtl): Diffuse color, Reflection glossiness, Refraction (Glass, Water), IOR, Translucency",
                "Texture Mapping: Bitmap textures, Procedural maps (Noise, Cellular, Gradient, Falloff), Normal maps, Bump maps, Displacement maps",
                "UVW Map modifier: Planar, Cylindrical, Spherical, Box mapping, Real-World Map Size alignment, Unwrap UVW basics"
            ]),
            ("Module 5: Photorealistic Lighting & Camera Setup", [
                "Photometric Lights: Target light, Free light, Sun & Sky systems, IES light profiles for interior luminaires",
                "V-Ray Lighting: VRaySun & VRaySky for daytime exterior scenes, VRayLight (Plane, Dome, Sphere, Mesh), HDRI environment lighting",
                "Physical Cameras: Exposure Control (EV, ISO, Shutter Speed, F-Number), Depth of Field (DoF), Motion Blur, Composition grids"
            ]),
            ("Module 6: Rendering, Animation & Post-Production", [
                "V-Ray Render Engine settings: Progressive vs Bucket, Image sampler, Global Illumination (Brute Force, Light Cache)",
                "Render Elements: VRayDenoiser, Cryptomatte, Lighting, Reflection, Refraction, ZDepth for post-processing",
                "Camera Walkthroughs: Keyframing, Path constraint animation, Safe frames, Preview animation",
                "Post-Production in Photoshop: Color grading, Contrast enhancement, Bloom/Glare effects, Background integration"
            ])
        ],
        "projects": [
            "Modern Residential Living Room Photorealistic Interior Render with Daytime & Night IES Lighting",
            "Luxury Contemporary Bungalow Exterior Architecture Visualization with Landscaping and HDRI Sky",
            "Cinematic Architectural Camera Walkthrough Animation Video of a Commercial Building"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Architectural Visualization Certificate."
    },
    {
        "code": "CIVIL-ADV-STEEL",
        "title": "AutoCAD Advance Steel (Structural Steel Detailing & Fabrication)",
        "field": "Civil CAD",
        "duration_months": 1.5,
        "total_fee": Decimal("16000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/civil-cad-courses/autocad-advance-steel-training-course-classes-institute-in-pune/",
        "overview": "Specialized course for steel detailers and structural engineers. Learn 3D structural steel modeling, automated parametric joint connections, industrial stairs and railings, fabrication shop drawings, and CNC data export.",
        "prerequisites": "Degree / Diploma in Civil or Mechanical Engineering with structural drafting knowledge.",
        "software_covered": ["Autodesk Advance Steel 2023 / 2024"],
        "modules": [
            ("Module 1: Advance Steel Environment & Project Setup", [
                "Advance Steel interface, Tool palettes, Project Explorer, Workplane manipulation",
                "Structural Grid systems, Curved grids, Level management",
                "Project Settings: Units, Drawing styles, Management Tools configuration"
            ]),
            ("Module 2: Structural Steel Elements Modeling", [
                "Standard Beams & Columns: I-sections, Channels, Angles, Hollow structural sections (RHS, SHS, CHS), T-bars",
                "Curved beams, Polybeams, Compound sections, Welded beams",
                "Steel Plates: Rectangular plates, Polygon plates, Circular plates, Folded plates",
                "Grating and Floor cladding, Special parts insertion"
            ]),
            ("Module 3: Parametric Steel Connections (Connection Vault)", [
                "Base Plate connections: Anchor bolts, Grout, Stiffener plates, Shear keys",
                "Beam-to-Column Joints: Clip angle, End plate (Moment / Shear), Fin plate, Flange weld joints",
                "Beam-to-Beam Connections: Coping, Web angle, Flush end plate, Splice joints",
                "Bracing Connections: Gusset plates, Tube bracing, Diagonal bracing, Middle gusset",
                "Purlin & Girt Connections with cleat angles"
            ]),
            ("Module 4: Secondary Steelwork & Miscellaneous Metal", [
                "Industrial Straight Stairs: Stringers, Treads, Landings, Connection to structure",
                "Spiral Stairs & Caged Ladders (Safety cages, Rungs, Exits)",
                "Handrails & Railings: Continuous handrails, Posts, Kick plates / Toe plates"
            ]),
            ("Module 5: Model Numbering, Audit & Clash Verification", [
                "Collision check, Technical audit, Steel joint verification",
                "Numbering Process: Single Part numbering, Assembly / Mark numbering, Prefix settings",
                "Managing revisions and design change propagation"
            ]),
            ("Module 6: Automated Fabrication Drawings & CNC Export", [
                "Drawing Processes: General Arrangement (GA) drawings, Anchor bolt layouts, 3D erection drawings",
                "Shop Drawings: Automated Single Part drawings and Assembly drawings with dimensions & welding callouts",
                "Bills of Materials (BOM): Material lists, Bolt lists, Cut lists, Loading lists",
                "NC & DXF Data Generation: DSTV format NC files for automated CNC cutting and drilling machines"
            ])
        ],
        "projects": [
            "Industrial Steel Warehouse Portal Frame with Full Parametric Connection Detailing",
            "Multi-Level Heavy Industrial Pipe Rack Steel Structure with Bracing and Base Plates",
            "Complete Fabrication Drawing Package (Single Part, Assembly, Erection Drawings, BOM & NC Files)"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Steel Detailing Certificate."
    },
    {
        "code": "CIVIL-PLANT-3D",
        "title": "AutoCAD Plant 3D (Process Piping & Plant Layout)",
        "field": "Civil CAD",
        "duration_months": 2,
        "total_fee": Decimal("18000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/civil-cad-courses/autocad-plant-3d-classes-training-institute-course-in-pune/",
        "overview": "Dedicated curriculum for process plant design, piping layouts, equipment modeling, and automated isometric drawings using Autodesk AutoCAD Plant 3D.",
        "prerequisites": "Diploma / Degree in Mechanical, Chemical, Petroleum, or Civil Engineering.",
        "software_covered": ["AutoCAD Plant 3D 2024", "AutoCAD P&ID", "Plant Spec Editor"],
        "modules": [
            ("Module 1: Plant 3D Project Setup & Standards", [
                "Plant 3D project configuration, folder structures, database selection (SQLite / SQL Server)",
                "Project Manager: Creating and managing P&ID, 3D piping, and Ortho drawings",
                "Spec Editor: Understanding piping specifications, catalogs, adding custom valves and fittings"
            ]),
            ("Module 2: P&ID Creation & Validation", [
                "Drawing pipelines, inline valves, instrument loops, equipment symbols",
                "Tagging and annotation rules, off-page connectors for multi-sheet P&IDs",
                "P&ID validation: Checking disconnected lines, mismatched diameters, unassigned tags"
            ]),
            ("Module 3: 3D Equipment Modeling", [
                "Parametric Equipment creation: Vertical/Horizontal Vessels, Centrifugal Pumps, Heat Exchangers, Storage Tanks",
                "Adding and modifying Nozzles: Pressure rating, Face type, Orientation, Elevation",
                "Converting custom AutoCAD 3D solid models into intelligent Plant 3D equipment"
            ]),
            ("Module 4: Spec-Driven 3D Pipe Routing", [
                "Spec-driven routing: Selecting pipe size, spec class (e.g. CS150, SS300), auto-fitting placement",
                "Routing with slope, branch creation via branch tables, inserting valves and specialty items",
                "Pipe supports: Placing hangers, shoes, guides, and custom support modeling"
            ]),
            ("Module 5: Structural Modeling in Plant 3D", [
                "Plant structural tools: Grid systems, Steel member placement (Beams, Columns, Braces)",
                "Platforms, Walkways, Industrial Ladders, Stairs, Railings around process equipment"
            ]),
            ("Module 6: Isometric & Orthographic Deliverables", [
                "Generating Production Isometrics (Iso themes, Bill of Materials, Spool drawings, PCF export)",
                "Generating Orthographic Drawings: Plans, Sections, Elevations with automatic pipe annotations",
                "Reporting: Generating Material Take-Off (MTO) and Line Lists, Exporting to Navisworks for clash checks"
            ])
        ],
        "projects": [
            "Industrial Boiler Room 3D Plant Layout with Steam & Condensate Piping",
            "Chemical Dosing Skid with Pump Equipment, Valve Manifolds, and Isometric Generation",
            "Plant MTO and Orthographic Drawing Package for Client Submittal"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Plant Design Certificate."
    },
    {
        "code": "CIVIL-NAVISWORKS",
        "title": "Autodesk Navisworks Manage (BIM Coordination, Clash Detection & 4D/5D Simulation)",
        "field": "Civil CAD",
        "duration_months": 1.5,
        "total_fee": Decimal("16000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/civil-cad-courses/navis-work-course-classes-training-institute-in-pune/",
        "overview": "Master multidisciplinary project coordination, 3D model aggregation, clash detection, 4D construction scheduling simulation, and 5D quantification using Autodesk Navisworks Manage.",
        "prerequisites": "Familiarity with AutoCAD, Revit, or 3D CAD/BIM models.",
        "software_covered": ["Autodesk Navisworks Manage 2024"],
        "modules": [
            ("Module 1: Navisworks Architecture & Navigation", [
                "Navisworks file formats: NWC (Cache), NWF (Federated File), NWD (Published Document)",
                "Merging multi-format models: Revit, AutoCAD, Plant 3D, SolidWorks, IFC, MicroStation",
                "Navigation tools: Walk, Fly, Orbit, Look Around, Third Person, Collision detection, Gravity",
                "Selection Tree, Selection Sets vs Search Sets (XML query-based dynamic sets)"
            ]),
            ("Module 2: Review, Measurement & Redlining", [
                "Measurement tools: Point-to-point, Area, Shortest distance, Cumulative, Transform/Move objects",
                "Review tools: Redline clouds, Text callouts, Drawing shapes, Tags, Comments, Hyperlinks",
                "Sectioning: Section planes, Section boxes, Moving and rotating section planes"
            ]),
            ("Module 3: Clash Detective (BIM Coordination)", [
                "Setting up Clash Tests: Hard Clash, Clearance Clash, Duplicate Clash with custom tolerances",
                "Rules: Ignore clashes in same layer, ignore clashes in same group, custom rule creation",
                "Clash Results: Status (New, Active, Reviewed, Approved, Resolved), Grouping clashes, Assigning responsibilities",
                "Generating Clash Reports: HTML, XML, Text, viewpoints export for Revit coordination"
            ]),
            ("Module 4: TimeLiner (4D Construction Scheduling)", [
                "TimeLiner overview: Tasks, Start/End dates, Task types (Construct, Demolish, Temporary)",
                "Linking to external project schedules: Microsoft Project, Primavera P6, CSV schedules",
                "Attaching 3D model geometry to schedule tasks using Search Sets",
                "Simulating construction sequence: Animation playback, visual appearance overrides, Exporting 4D video"
            ]),
            ("Module 5: Animator & Scripter (Interactive Animations)", [
                "Animator: Creating animation sets, Keyframing camera movement, animating geometry (crane movement, doors)",
                "Scripter: Creating interactive triggers (On key press, On collision, On timer) to execute events"
            ]),
            ("Module 6: Quantification (5D BIM Costing) & Rendering", [
                "Quantification setup: Uniformat, MasterFormat, Custom Item & Resource catalogs",
                "Model Takeoff vs Virtual Takeoff (manual measurement of missing elements), Change tracking",
                "Autodesk Rendering: Applying materials, Sun/Sky lighting, Rendering high-resolution viewpoints"
            ])
        ],
        "projects": [
            "Commercial High-Rise Multi-Disciplinary (Arch + Struct + MEP) Clash Detection & Resolution Report",
            "4D Construction Sequence Timeline Simulation for a Stadium Project linked with Primavera P6",
            "5D Quantification Takeoff and Material Summary for Concrete and Steel Structure"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized BIM Coordination Certificate."
    },
    {
        "code": "BIM-ARCH-DESIGN",
        "title": "Architectural Design & Visualization Master Track",
        "field": "Design & BIM",
        "duration_months": 6,
        "total_fee": Decimal("35000.00"),
        "source_url": "https://graphixtechnoservices.com/architectural-design-course/",
        "overview": "Full-stack architectural design program spanning 2D drafting, 3D BIM parametric architecture, photorealistic CGI rendering, space planning, and municipal bye-laws. Covers AutoCAD, Revit Architecture, 3ds Max with V-Ray, and Photoshop.",
        "prerequisites": "B.Arch, Diploma / Degree in Civil / Interior Design, or creative professionals.",
        "software_covered": ["AutoCAD", "Autodesk Revit Architecture", "Autodesk 3ds Max", "V-Ray", "Adobe Photoshop"],
        "modules": [
            ("Track 1: Architectural Concept & 2D Municipal Drafting", [
                "Architectural space planning, circulation, zoning, anthropometry, NBC/FSI standards",
                "AutoCAD architectural drawing package: Floor plans, Elevations, Cross-sections, Site plans, Area statements"
            ]),
            ("Track 2: Parametric Building Information Modeling (Revit)", [
                "3D architectural modeling: Walls, Doors, Windows, Roofs, Curtain Walls, Custom Stairs, Railings",
                "Parametric family creation, Site planning & topography, Quantity schedules and material takeoffs",
                "Construction documentation, Working drawings, Sheet setup, Phasing and Design Options"
            ]),
            ("Track 3: Architectural Visualization & CGI (3ds Max & V-Ray)", [
                "High-poly modeling of architectural interiors, facades, and landscape elements",
                "V-Ray physically accurate materials: Wood veneers, Marble, Polished concrete, Architectural glass, Fabrics",
                "Lighting masterclass: Natural daylighting, Golden hour sun, Artificial IES photometric luminaires",
                "Cinematic camera composition, High-resolution rendering, Post-production color grading in Photoshop"
            ]),
            ("Track 4: Professional Architectural Portfolio & Capstone", [
                "Developing a complete commercial / residential architectural portfolio project from concept sketches to working drawings, marketing CGI renders, and presentation boards"
            ])
        ],
        "projects": [
            "Comprehensive Design & Working Drawings for a 10-Acre Mixed-Use Residential & Commercial Township",
            "Photorealistic Exterior and Interior CGI Visualization Portfolio for Luxury High-End Penthouse",
            "BIM Coordinated Architectural Execution Set with Full Door/Window/Finishes Schedules"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized Architectural Design Professional Certificate."
    },
    {
        "code": "BIM-PROFESSIONAL",
        "title": "BIM (Building Information Modeling) Professional Track",
        "field": "Design & BIM",
        "duration_months": 6,
        "total_fee": Decimal("38000.00"),
        "source_url": "https://graphixtechnoservices.com/bim-design-course/",
        "overview": "Master Building Information Modeling across Architecture, Structure, MEP, and Construction Management. Fully aligned with ISO 19650 standards. Covers Revit Architecture, Revit Structure, Revit MEP, Navisworks Manage, and Autodesk Construction Cloud / BIM 360.",
        "prerequisites": "BE/B.Tech/Diploma in Civil, Mechanical, Electrical Engineering, or Architecture.",
        "software_covered": ["Revit Architecture", "Revit Structure", "Revit MEP", "Navisworks Manage", "BIM 360 / ACC"],
        "modules": [
            ("Module 1: BIM Framework, Standards & ISO 19650", [
                "BIM Maturity Levels (Level 0 to Level 3), ISO 19650 principles, Common Data Environment (CDE)",
                "Level of Development (LOD 100, 200, 300, 350, 400, 500) specifications",
                "BIM Execution Plan (BEP / BXP) structure, Employer's Information Requirements (EIR), Information Delivery Table"
            ]),
            ("Module 2: Multi-Disciplinary BIM Authoring", [
                "Revit Architecture: Parametric building modeling, spatial planning, schedules, construction documents",
                "Revit Structure: Foundations, framing, structural steel joints, 3D rebar modeling and BBS",
                "Revit MEP: HVAC ductwork, hydronic piping, plumbing sanitary/water supply, electrical power/lighting"
            ]),
            ("Module 3: Federated Model Coordination & Clash Management", [
                "Navisworks model aggregation: Assembling multi-disciplinary models, Shared coordinates alignment",
                "Clash Detective: Hard vs Clearance clash matrix, Grouping clashes, Clash reporting, BCF (BIM Collaboration Format) workflows"
            ]),
            ("Module 4: 4D Time Scheduling & 5D Cost Takeoff", [
                "4D Construction Sequencing in Navisworks TimeLiner linked with Primavera P6 / MS Project",
                "5D Quantity takeoff, QTO mapping with cost estimation databases, Progress tracking"
            ]),
            ("Module 5: Cloud Collaboration on Autodesk BIM 360 / ACC", [
                "Autodesk Construction Cloud (ACC) & BIM 360 Docs: Permission management, Model Coordination, Issue tracking, Design Collaboration, Version comparison",
                "As-built BIM model handover, COBie data standards for Facility Management"
            ])
        ],
        "projects": [
            "Smart Metro Station Multi-Discipline BIM Project (Arch + Struct + MEP) with Clash-Free Sign-Off",
            "Hospital Building 4D Construction Sequence & 5D Cost Estimation Simulation",
            "BIM Execution Plan (BEP) and CDE Cloud Setup for International Infrastructure Project"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized BIM Professional Certificate."
    },
    {
        "code": "BIM-INTERIOR-DESIGN",
        "title": "Interior Design & Space Planning Masterclass",
        "field": "Design & BIM",
        "duration_months": 4,
        "total_fee": Decimal("25000.00"),
        "source_url": "https://graphixtechnoservices.com/interior-design-course/",
        "overview": "Complete professional interior design program covering residential, commercial, and retail spaces. Learn design theory, space planning, AutoCAD working drawings, 3ds Max / V-Ray 3D visualization, materials, and modular joinery detailing.",
        "prerequisites": "Any graduate, diploma holder, or creative professional with an interest in interior styling.",
        "software_covered": ["AutoCAD (Interior)", "Autodesk 3ds Max", "V-Ray", "Adobe Photoshop"],
        "modules": [
            ("Module 1: Design Fundamentals & Space Planning", [
                "Elements & Principles of Design: Harmony, Balance, Proportion, Rhythm, Focal point",
                "Color Theory: Color wheel, Color psychology, Warm vs Cool palettes, Mood board creation",
                "Anthropometry & Ergonomics: Human body dimensions, Clearances for furniture, ADA accessibility",
                "Space Planning: Residential zoning (Living, Dining, Kitchen, Master bedroom), Commercial office layouts"
            ]),
            ("Module 2: 2D Working Drawings & Millwork Detailing", [
                "AutoCAD 2D Interior Drawings: Furniture layouts, Dimension plans, Partition plans",
                "Reflected Ceiling Plan (RCP): False ceiling design, Cove lighting, Trap doors, Diffuser locations",
                "Flooring Layout: Tile/marble patterns, Skirting details, Inlay designs",
                "Joinery / Millwork Working Drawings: Modular Kitchen (carcass, shutters, hardware, pull-outs), Wardrobes, Vanity counters, TV Units, Paneling"
            ]),
            ("Module 3: Materials, Finishes & MEP Services for Interiors", [
                "Materials: Plywood (BWP/BWR), MDF, HDF, Veneers, Laminates, Solid Surface / Corian, Quartz, Natural Stones, Glass, Fabrics",
                "Plumbing & Sanitary fixtures selection, Electrical layout (Switchboard heights, Appliance points), HVAC coordinate drawings"
            ]),
            ("Module 4: 3D Visualization & Photorealistic Rendering", [
                "3ds Max modeling of custom furniture, curtains, modular units, and decorative props",
                "V-Ray material setup: Fabric weaves, Polished marble, Brushed brass, Wood grain reflections",
                "Lighting scenes: Day scene, Warm evening cozy lighting, Downlights, LED strip cove lighting",
                "Rendering camera angles and post-production styling in Photoshop"
            ]),
            ("Module 5: Estimation, BOQ & Site Execution Management", [
                "Preparation of Bill of Quantities (BOQ), Rate analysis, Vendor quotations",
                "Site execution checklist, Contractor coordination, Material quality checking, Handover protocol"
            ])
        ],
        "projects": [
            "Luxury 3-BHK Residential Apartment Complete Interior Design & Working Drawing Package",
            "Modern Corporate Co-Working Space Planning with Ergonomic Workstations and Lounge Areas",
            "Photorealistic 3D Rendering Portfolio with Mood Boards and Material BOQ"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Interior Design Certificate."
    },
    {
        "code": "CIVIL-STRUCT-DESIGN",
        "title": "Structural Design & Analysis Engineering Masterclass",
        "field": "Civil CAD",
        "duration_months": 5,
        "total_fee": Decimal("30000.00"),
        "source_url": "https://graphixtechnoservices.com/structural-design-course/",
        "overview": "Rigorous structural engineering program covering RCC and structural steel design as per Indian (IS) and International (ACI/AISC) codes. Covers structural mechanics, load calculation, ETABS / STAAD.Pro analysis, Revit Structure BIM, and Advance Steel.",
        "prerequisites": "BE/B.Tech in Civil or Structural Engineering.",
        "software_covered": ["AutoCAD", "Revit Structure", "Advance Steel", "ETABS / STAAD.Pro / Robot Structural Analysis"],
        "modules": [
            ("Module 1: Structural Mechanics & Building Codes", [
                "Structural behavior: Bending, Shear, Torsion, Axial compression/tension, Deflection limits",
                "Codes & Standards: IS 456 (Plain and Reinforced Concrete), IS 800 (General Construction in Steel), IS 875 Parts 1-5 (Design Loads: Dead, Live, Wind), IS 1893 (Criteria for Earthquake Resistant Design), IS 13920 (Ductile Detailing of RCC)"
            ]),
            ("Module 2: Load Calculations & Structural Modeling", [
                "Dead Load and Superimposed Dead Load calculation, Live load distribution on slabs",
                "Wind Load calculation: Basic wind speed, Risk coefficient (k1), Terrain factor (k2), Topography factor (k3), Design wind pressure (Pz)",
                "Seismic Load analysis: Seismic Zone factor (Z), Importance factor (I), Response reduction factor (R), Equivalent Static vs Response Spectrum method",
                "3D Finite Element Modeling of building frames, shear walls, and diaphragm assignments"
            ]),
            ("Module 3: Reinforced Concrete Design (RCC)", [
                "Slab Design: One-way, Two-way, Flat slabs, Sunk slabs",
                "Beam Design: Singly reinforced, Doubly reinforced, Flanged beams (T & L beams), Shear reinforcement",
                "Column Design: Short and slender columns, Uniaxial and Biaxial bending, P-M interaction curves",
                "Foundation Design: Isolated footings, Combined footings, Raft/Mat foundations, Pile foundations",
                "Retaining Walls & Water Tanks design basics"
            ]),
            ("Module 4: Structural Steel Design & PEB", [
                "Steel Tension & Compression members: Slenderness ratio, Column buckling curves",
                "Steel Beams: Lateral Torsional Buckling (LTB), Compact and Non-compact sections",
                "Connections: Welded and Bolted connections, High-strength friction grip (HSFG) bolts",
                "Pre-Engineered Buildings (PEB): Tapered rafters, Tapered columns, Purlins, Sag rods, Wind bracings"
            ]),
            ("Module 5: BIM Rebar Detailing & Advance Steel Fabrication", [
                "Revit Structure: 3D rebar modeling, Ductile detailing as per IS 13920, Automatic BBS generation",
                "Advance Steel: Steel frame modeling, Connection vault detailing, Shop drawings, NC data export"
            ])
        ],
        "projects": [
            "Earthquake-Resistant G+12 Story RCC Commercial Tower Analysis, Design & Rebar Detailing",
            "45-Meter Clear Span Industrial PEB Warehouse Design with Advance Steel Fabrication Drawings",
            "Structural Analysis & Foundation Design for Deep Basement Excavation with Retaining Walls"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized Structural Design Engineer Certificate."
    },

    # =========================================================================
    # DISCIPLINE 3: ELECTRICAL CAD & MEP
    # =========================================================================
    {
        "code": "ELEC-AUTOCAD",
        "title": "Electrical AutoCAD (Schematics, Wiring & Control Panel Layouts)",
        "field": "Electrical CAD",
        "duration_months": 2,
        "total_fee": Decimal("15000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/electrical-courses/electrical-autocad/",
        "overview": "Professional electrical computer-aided design training using AutoCAD Electrical toolset. Learn control schematics, ladder diagrams, PLC I/O wiring, terminal block design, panel layout fabrication drawings, and automated bill of materials.",
        "prerequisites": "Diploma / Degree in Electrical, Electronics, Instrumentation, or Mechatronics Engineering.",
        "software_covered": ["AutoCAD Electrical 2023 / 2024"],
        "modules": [
            ("Module 1: Electrical Project Setup & Standards", [
                "AutoCAD Electrical interface, Project Manager, Project files (.wdp), Drawing properties (.wdd)",
                "Standard symbol libraries: IEC, JIC, NFPA, IEEE, JIS standards",
                "Ladder diagrams: Rung spacing, Width, Multi-phase ladders, Reference numbers"
            ]),
            ("Module 2: Schematic Wiring & Point-to-Point Circuits", [
                "Wire routing: Wires, Multi-conductor cables, Wire crossing loops vs Gaps, 45-degree bevels",
                "Automated Wire Numbering: Wire number placement, Sequential vs Line reference numbering",
                "Signal Arrows: Source & Destination arrows, Cross-referencing between sheets"
            ]),
            ("Module 3: Schematic Electrical Components", [
                "Inserting Components: Push buttons, Selector switches, Relays, Contactors, Fuses, Transformers, Motors",
                "Component Tagging: IEC/NFPA tag conventions, Descriptions, Ratings, Cross-sheet references",
                "Parent-Child Relationships: Relay coils and associated NO/NC contacts with automatic pin lists",
                "Catalog Lookup: Assigning manufacturer part numbers (Siemens, Schneider, ABB, Rockwell)"
            ]),
            ("Module 4: PLC I/O Modules & Automated Addressing", [
                "Parametric PLC Modules: Digital Input, Digital Output, Analog Input, Analog Output cards",
                "PLC Addressing formats (Rack/Slot/Bit, Hexadecimal, Octal), I/O Wire connections",
                "Spreadsheet-to-PLC I/O drawing generation tool"
            ]),
            ("Module 5: Control Panel Layouts & Enclosures", [
                "Creating Panel Layout drawings from schematic component lists",
                "Cabinet Enclosures: Wall-mounted, Free-standing panels, Sizing enclosures",
                "Din Rails, Cable Trays, Wire Ducts placement, Component Footprints insertion with true dimensions",
                "Nameplates, Terminal Blocks, and Legend plates placement"
            ]),
            ("Module 6: Terminal Strips & Automated Documentation", [
                "Terminal Strip Editor (TSE): Multi-tier terminals, Jumpers, Spares, Cable connections",
                "Generating Automated Reports: Bill of Materials (BOM), From/To Wire Lists, Component Lists, Cable Schedules",
                "Publishing multi-sheet project drawing packages to PDF with intelligent hyperlinks"
            ])
        ],
        "projects": [
            "Industrial Motor Control Center (MCC) Panel Schematic & 2D Panel Layout Drawing",
            "Automated Packaging Machine PLC Control Wiring Diagram with Terminal Strip Details",
            "Complete Electrical Schematics & BOM Generation for Solar Inverter Control Panel"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized Electrical CAD Certificate."
    },
    {
        "code": "MEP-REVIT-MEP",
        "title": "Autodesk Revit MEP (Mechanical, Electrical, Plumbing BIM Modeling)",
        "field": "Electrical CAD",
        "duration_months": 3,
        "total_fee": Decimal("22000.00"),
        "source_url": "https://graphixtechnoservices.com/courses/electrical-courses/revit-mep-training-in-pune/",
        "overview": "Comprehensive 14-chapter curriculum in Autodesk Revit MEP covering HVAC ductwork, mechanical piping, domestic water and sanitary drainage plumbing, and electrical power, lighting, cable tray, and conduit modeling with inter-disciplinary coordination.",
        "prerequisites": "BE/B.Tech/Diploma in Electrical, Mechanical, Civil Engineering or MEP Draftsmen.",
        "software_covered": ["Autodesk Revit 2024 (MEP)", "Navisworks integration"],
        "modules": [
            ("Chapter 1-3: MEP Environment, Navigation & Editing Tools", [
                "Chapter 1: MEP Interface, Ribbon menus, System Browser, Project Browser organization, Central vs Local files",
                "Chapter 2: Basic Creation Tools: Detach from central, Creating local projects, 2D/3D Navigation",
                "Chapter 3: Basic Editing Tools: Filter selection, Align, Pin/Unpin, Copy/Paste, Arrays, Trim/Extend, Groups"
            ]),
            ("Chapter 4-6: Project Setup, Views & Component Families", [
                "Chapter 4: Starting an MEP Project: Linking Architectural & Structural models, Shared Coordinates, Copy/Monitor levels & grids",
                "Chapter 5: Views & Visibility: Discipline views (Mechanical, Electrical, Plumbing, Coordination), View Templates, Crop regions",
                "Chapter 6: Component Families: Out-of-the-box MEP families, Connectors (Duct, Pipe, Electrical), Flow direction, System classification"
            ]),
            ("Chapter 7-9: Spaces, HVAC Systems & Duct Sizing", [
                "Chapter 7: Spaces & Zones: Room tags vs Space tags, Space volume calculations, Heating & Cooling load analysis",
                "Chapter 8: Mechanical Systems: System Browser hierarchy, Graphic Overrides, System Inspector, Duct sizing algorithms",
                "Chapter 9: HVAC Ductwork: Duct types (Rectangular, Round, Oval), Routing preferences, Air terminals (Diffusers, Grilles), In-line equipment (VAV boxes, Dampers), Flexible ducts"
            ]),
            ("Chapter 10-11: Hydronic Piping & Plumbing Systems", [
                "Chapter 10: Hydronic Piping Systems: Chilled water supply/return, Pipe materials (Copper, Carbon Steel, PVC), Pipe fittings, Valves, In-line accessories",
                "Chapter 11: Plumbing Systems: Domestic cold/hot water, Soil/Waste/Vent piping, Sloped drainage pipes, Plumbing fixtures (WC, Urinals, Basins, Floor drains), Cleanouts"
            ]),
            ("Chapter 12-14: Electrical Systems, Detailing & Documentation", [
                "Chapter 12: Electrical Systems: Lighting fixtures, Power receptacles, Equipment connections, Panel boards, Circuiting, Cable Trays and Conduits routing",
                "Chapter 13: Detailing: Detail lines, Insulation, Repeating details, 3D section box detailing, Revision clouds",
                "Chapter 14: Documentation: Setting up sheets, Title blocks, Adding views, Duct/Pipe schedules, Electrical panel schedules, Exporting to DWG/PDF"
            ])
        ],
        "projects": [
            "Commercial Office Building Complete MEP BIM Coordinated Model (HVAC + Plumbing + Electrical)",
            "Hospital Ward Building Medical Gas, Plumbing Drainage, and Cable Tray Distribution Layout",
            "Multi-Disciplinary Clash Detection and Automated MEP Quantity Schedule Extraction"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized Revit MEP Professional Certificate."
    },
    {
        "code": "ELEC-DESIGN",
        "title": "Electrical Design Engineering (Substations, Power Distribution & Lighting)",
        "field": "Electrical CAD",
        "duration_months": 3,
        "total_fee": Decimal("22000.00"),
        "source_url": "https://graphixtechnoservices.com/electrical-design-course/",
        "overview": "Professional electrical design engineering program for commercial complexes, industrial plants, and substations. Covers load estimation, single-line diagrams (SLD), transformer and DG sizing, short-circuit calculations, cable sizing, earthing design, and Dialux lighting.",
        "prerequisites": "Degree / Diploma in Electrical or Electrical & Electronics Engineering.",
        "software_covered": ["AutoCAD Electrical", "DIALux evo", "ETAP fundamentals", "Revit MEP Electrical"],
        "modules": [
            ("Module 1: Power Systems & Regulatory Standards", [
                "Generation, Transmission & Distribution overview, Grid connections, Tariff structures",
                "Codes & Standards: National Electrical Code (NEC), Indian Electricity Rules (IE Rules), IS 732 (Wiring installations), IS 3043 (Earthing practice), IS/IEC 62305 (Lightning Protection), NBC 2016"
            ]),
            ("Module 2: Electrical Load Estimation & Equipment Sizing", [
                "Connected Load, Maximum Demand, Diversity Factor, Demand Factor, Power Factor improvement",
                "Transformer Sizing: KVA rating calculations, Percentage impedance, Vector groups, Oil-type vs Dry-type",
                "Diesel Generator (DG) Sizing: Base load, Starting KVA of motors, Step loading, AMF panel logic",
                "Uninterruptible Power Supply (UPS) & Battery Bank Sizing for critical loads"
            ]),
            ("Module 3: Substation & Switchgear Design", [
                "Indoor & Outdoor Substations: 33kV/11kV to 415V transformation, Yard layouts, Clearances",
                "Medium Voltage (MV) & Low Voltage (LV) Switchgear: Air Circuit Breakers (ACB), VCB, SF6 breakers, MCCB, MCB, RCD",
                "Busbar Sizing: Copper vs Aluminum busbars, Ampacity, Temperature rise, Short circuit withstand rating",
                "Motor Control Centers (MCC) & Power Control Centers (PCC) single-line diagrams (SLD)"
            ]),
            ("Module 4: Cable Sizing & Voltage Drop Calculations", [
                "Cable types: XLPE, PVC, Armored, Unarmored, Copper vs Aluminum conductors",
                "Cable Sizing Criteria: Continuous current carrying capacity, Derating factors (Ambient temperature, Grouping, Soil depth)",
                "Voltage drop calculation (Running & Motor starting conditions, Permissible limits as per code)",
                "Short circuit temperature rise withstand capability"
            ]),
            ("Module 5: Interior & Exterior Lighting Design (DIALux evo)", [
                "Lighting Fundamentals: Luminous flux (Lumens), Illuminance (Lux), Efficacy, Color Rendering Index (CRI), CCT",
                "Lighting standards as per IS 3646 and IESNA for offices, factories, hospitals, parking",
                "DIALux evo: Room modeling, Luminaire import (IES/LDT files), Light calculation, False-color rendering, Emergency lighting design"
            ]),
            ("Module 6: Earthing, Lightning Protection & ELV Systems", [
                "Earthing Design (IS 3043): Pipe earthing, Plate earthing, Chemical earthing, Touch & Step potential calculations, Earth pit sizing",
                "Lightning Protection Design (IS/IEC 62305): Risk assessment, Rolling sphere method, Down conductors, Air terminals",
                "Extra Low Voltage (ELV) Systems: Fire Alarm System (Smoke/Heat detectors, MCP, Panels as per NFPA 72), CCTV, Access Control, Public Address (PA) systems"
            ])
        ],
        "projects": [
            "Complete Electrical Power Distribution & SLD for a 100,000 sq.ft Corporate IT Park",
            "Indoor 11kV/415V Substation Equipment Layout with Transformer, DG, and Earthing Grid Design",
            "DIALux evo Photometric Lighting Simulation and Emergency Lighting Layout for Commercial Showroom"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized Electrical Design Engineer Certificate."
    },

    # =========================================================================
    # DISCIPLINE 4: IT, SOFTWARE & CLOUD TECHNOLOGIES
    # =========================================================================
    {
        "code": "IT-CORE-JAVA",
        "title": "Core Java Programming (Java SE 17 / 21 LTS Masterclass)",
        "field": "IT & Software Development",
        "duration_months": 2,
        "total_fee": Decimal("12000.00"),
        "source_url": "https://graphixtechnoservices.com/core-java-course/",
        "overview": "Industry-aligned Core Java programming course covering fundamental syntax, object-oriented programming (OOP), collections framework, multithreading, exception handling, file I/O, and modern Java 8+ features (Streams, Lambdas).",
        "prerequisites": "Basic understanding of programming logic or computer science fundamentals.",
        "software_covered": ["Java SE 17 / 21 LTS", "IntelliJ IDEA / Eclipse", "Git & GitHub"],
        "modules": [
            ("Section 1: Java Basics & Execution Architecture", [
                "Java History, features, Platform Independence (WORA), JDK vs JRE vs JVM architecture",
                "Java program syntax, Compilation and Execution flow, Bytecode and JIT compiler",
                "Variables, Datatypes (Primitive vs Non-primitive), Type Casting (Implicit vs Explicit)",
                "Operators (Arithmetic, Relational, Logical, Bitwise, Assignment, Ternary)",
                "Control Statements: if-else, nested if, switch-case (Traditional & Enhanced Switch expressions)",
                "Loops: for loop, enhanced for-each, while loop, do-while, break and continue statements"
            ]),
            ("Section 2: Object-Oriented Programming (OOP) Principles", [
                "Classes and Objects: State and Behavior, Memory allocation in Heap and Stack",
                "Methods: Method declaration, Parameters, Return types, Method Overloading",
                "Constructors: Default, Parameterized, Constructor Overloading, 'this' keyword and constructor chaining",
                "Static keyword: Static variables, Static methods, Static blocks vs Instance initialization blocks",
                "Inheritance: Single, Multilevel, Hierarchical inheritance, 'super' keyword",
                "Polymorphism: Compile-time (Method Overloading) vs Runtime (Method Overriding, Dynamic Method Dispatch)",
                "Abstraction: Abstract classes, Abstract methods, Interfaces (Multiple inheritance via interfaces, default & static methods)",
                "Encapsulation: Access Specifiers (private, default, protected, public), Getters and Setters, Java Beans, Singleton Class pattern"
            ]),
            ("Section 3: Core Java APIs, Exceptions & Collections Framework", [
                "Strings in Java: String immutability, String pool, String vs StringBuilder vs StringBuffer",
                "Arrays: 1D arrays, 2D arrays, Arrays class utility methods",
                "Wrapper Classes, Autoboxing and Unboxing, Object class methods (equals, hashCode, toString)",
                "Exception Handling: Exception hierarchy, Checked vs Unchecked exceptions, try, catch, finally, throw, throws, Custom exceptions",
                "Multithreading: Thread lifecycle, Creating threads (Thread class vs Runnable interface), Thread synchronization, Deadlocks, Inter-thread communication",
                "Collections Framework: Collection hierarchy, List (ArrayList, LinkedList, Vector), Set (HashSet, LinkedHashSet, TreeSet), Queue & Deque",
                "Map Interface: HashMap, LinkedHashMap, TreeMap, Hashtable, Iterating maps",
                "Generics, Comparable and Comparator interfaces for custom sorting",
                "File Handling & I/O: File, FileReader, FileWriter, BufferedReader, BufferedWriter, Serialization & Deserialization"
            ]),
            ("Section 4: Modern Java 8+ Functional Programming", [
                "Lambda Expressions, Functional Interfaces (@FunctionalInterface, Predicate, Function, Consumer, Supplier)",
                "Stream API: Filtering, Mapping, Sorting, Reducing, Collectors (toList, toSet, groupingBy)",
                "Optional class to eliminate NullPointerExceptions, Method References, Date & Time API (java.time package)"
            ])
        ],
        "projects": [
            "Bank Account Management Console Application with Transaction History & Serialization",
            "Student Examination Grading & Record System using Java Collections & Custom Sorting",
            "Multi-Threaded Producer-Consumer Inventory Simulation System"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Core Java Certificate."
    },
    {
        "code": "IT-ADV-JAVA",
        "title": "J2EE & Advanced Java Frameworks (Spring Boot, Hibernate & REST)",
        "field": "IT & Software Development",
        "duration_months": 2.5,
        "total_fee": Decimal("18000.00"),
        "source_url": "https://graphixtechnoservices.com/j2ee-advance-java/",
        "overview": "Master enterprise Java development covering JDBC, Servlets, JSP, Hibernate ORM, Spring Framework, Spring Boot, Spring Data JPA, and secure RESTful web service development.",
        "prerequisites": "Proficiency in Core Java programming and SQL database basics.",
        "software_covered": ["Java SE 17/21", "Spring Boot 3", "Hibernate 6", "PostgreSQL / MySQL", "Postman", "Maven"],
        "modules": [
            ("Section 1: Database Connectivity & Web Foundations", [
                "JDBC Architecture, JDBC Driver types, DriverManager, Connection, Statement, PreparedStatement, CallableStatement",
                "CRUD operations using JDBC, Batch processing, Transaction management, Connection Pooling (HikariCP)",
                "Java Servlets: Web server vs Application server, Servlet lifecycle (init, service, destroy), HttpServletRequest & HttpServletResponse",
                "Session Management: Cookies, HttpSession, URL Rewriting, Hidden form fields, Servlet Filters and Listeners",
                "JSP (JavaServer Pages): Lifecycle, Scripting elements (Scriptlet, Expression, Declaration), Directives, JSTL (Core, Formatting), Expression Language (EL), MVC architecture"
            ]),
            ("Section 2: Hibernate ORM Framework", [
                "Object-Relational Mapping (ORM) concepts, Problems with JDBC, Hibernate Architecture",
                "Configuration and SessionFactory, Session, Transaction, Entity mapping annotations (@Entity, @Table, @Id, @GeneratedValue, @Column)",
                "Entity Relationships: @OneToOne, @OneToMany, @ManyToOne, @ManyToMany, Cascade types, Fetch types (Eager vs Lazy)",
                "HQL (Hibernate Query Language), Native SQL, Criteria API, First-level cache vs Second-level cache (Ehcache)"
            ]),
            ("Section 3: Spring Framework & Spring Boot", [
                "Spring Core: Inversion of Control (IoC), Dependency Injection (DI) - Constructor vs Setter injection",
                "Spring Bean lifecycle, Component scanning, Annotations (@Component, @Service, @Repository, @Autowired, @Qualifier, @Value)",
                "Spring Boot introduction: Auto-configuration, Starter dependencies, application.properties / application.yml, Embedded Tomcat",
                "Spring MVC architecture: DispatcherServlet, @Controller, @RestController, @RequestMapping, @GetMapping, @PostMapping, @PathVariable, @RequestParam, @RequestBody"
            ]),
            ("Section 4: Spring Data JPA, REST APIs & Security", [
                "Spring Data JPA: JpaRepository, CrudRepository, Finder methods, @Query annotation, Pagination and Sorting",
                "Building RESTful Web Services: Richardson Maturity Model, HTTP status codes, DTO pattern, Exception Handling with @ControllerAdvice and @ExceptionHandler",
                "Bean Validation using Jakarta Validation (@NotNull, @Size, @Email, @Pattern)",
                "Spring Security fundamentals: Authentication vs Authorization, Password encryption (BCrypt), JWT (JSON Web Token) token-based authentication",
                "API Documentation using Swagger / OpenAPI 3, Testing APIs with Postman"
            ])
        ],
        "projects": [
            "Enterprise Employee Leave Management System using Servlets, JSP, and MySQL",
            "Hospital Patient Appointment Booking RESTful API with Spring Boot & Spring Data JPA",
            "Secure E-Commerce Backend Service with JWT Authentication, Shopping Cart, and Database Transactions"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Enterprise Java Certificate."
    },
    {
        "code": "IT-JAVA-FULLSTACK",
        "title": "Java Full Stack Developer (React.js, Spring Boot, Microservices & Cloud)",
        "field": "IT & Software Development",
        "duration_months": 6,
        "total_fee": Decimal("35000.00"),
        "source_url": "https://graphixtechnoservices.com/java-full-stack-developer-course/",
        "overview": "End-to-end full stack web development program. Master modern frontend development with HTML5, CSS3, JavaScript ES6+, Bootstrap, and React.js paired with enterprise backend engineering using Core Java, Spring Boot, Hibernate, MySQL, Docker, and Git.",
        "prerequisites": "Any graduate / engineering student with basic logical aptitude and passion for software development.",
        "software_covered": ["React.js", "JavaScript ES6+", "HTML5/CSS3/Bootstrap", "Java 17/21", "Spring Boot", "MySQL/PostgreSQL", "Docker", "Git/GitHub", "Postman"],
        "modules": [
            ("Phase 1: Frontend Web Development (HTML5, CSS3, Bootstrap)", [
                "HTML5 semantic layout elements (header, nav, main, section, article, footer), forms, inputs, tables, media",
                "CSS3 Styling: Box model, Selectors, Colors, Fonts, Flexbox, CSS Grid, Media queries, Responsive design",
                "Bootstrap 5 / Tailwind CSS: Grid system, Components (Navbar, Cards, Modals, Forms, Alerts, Carousels)"
            ]),
            ("Phase 2: Modern JavaScript (ES6+)", [
                "Variables (let, const), Data types, Functions (Arrow functions, Higher-order functions, Callbacks)",
                "DOM Manipulation: Selecting elements, Event listeners, Modifying classes, attributes, dynamic HTML creation",
                "ES6+ Features: Destructuring, Spread/Rest operators, Template literals, Modules (import/export)",
                "Asynchronous JavaScript: Event loop, Promises, Async/Await, Fetch API, Axios for HTTP requests"
            ]),
            ("Phase 3: React.js Frontend Framework", [
                "React introduction, Virtual DOM, JSX syntax, Component-based architecture (Functional components)",
                "Props and State management, Handling user events, Conditional rendering, Lists and Keys",
                "React Hooks: useState, useEffect, useRef, useMemo, useCallback, useContext",
                "React Router DOM: Single Page Application (SPA) routing, Nested routes, Protected routes, URL params",
                "Form Handling with React Hook Form / Formik, Axios HTTP client, Toast notifications, UI Component Libraries (Material UI)"
            ]),
            ("Phase 4: Backend Engineering with Core & Advanced Java", [
                "Core Java Programming: OOP, Exception handling, Collections framework, Multithreading, Streams & Lambdas",
                "Relational Database Management (RDBMS): SQL queries, DDL, DML, Joins, Grouping, Indexing, Transactions (ACID)",
                "Spring Boot 3: Dependency Injection, REST controllers, Spring Data JPA, Hibernate ORM, Entity relationships"
            ]),
            ("Phase 5: Full Stack Integration, Security & DevOps", [
                "Connecting React frontend to Spring Boot backend: CORS configuration, Axios interceptors",
                "Security: Spring Security 6 with JWT (JSON Web Tokens), Role-based access control (Admin, Student, Counselor)",
                "Unit & Integration Testing: JUnit 5, Mockito for backend; React Testing Library basics",
                "DevOps Tools: Git & GitHub version control (Branching, PRs, Merge conflicts), Docker containerization of React and Spring Boot apps, Deploying to cloud (Render / AWS)"
            ])
        ],
        "projects": [
            "Coaching Institute Management System (React.js Frontend + Spring Boot Backend + MySQL Database + JWT Auth)",
            "Real-Time E-Commerce Web Application with Product Catalog, Shopping Cart, and Stripe Payment Gateway",
            "Social Media / Discussion Forum Platform with User Profiles, Comments, Likes, and File Uploads"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized Full Stack Developer Certificate."
    },
    {
        "code": "CLOUD-AWS-ARCH",
        "title": "AWS Cloud Solutions Architect (Associate SAA-C03 Certified Track)",
        "field": "Cloud Computing",
        "duration_months": 2.5,
        "total_fee": Decimal("20000.00"),
        "source_url": "https://graphixtechnoservices.com/aws-certification-course/",
        "overview": "Comprehensive cloud computing and DevOps architecture program aligned with the AWS Certified Solutions Architect Associate (SAA-C03) curriculum. Master IAM, EC2, VPC networking, S3, RDS, Auto Scaling, Route 53, Serverless Lambda, and Cloud Security.",
        "prerequisites": "Basic understanding of networking concepts, operating systems, or programming.",
        "software_covered": ["Amazon Web Services (AWS)", "AWS CLI", "AWS CloudShell", "Terraform basics"],
        "modules": [
            ("Module 1: Cloud Fundamentals & AWS Global Infrastructure", [
                "Cloud computing models (IaaS, PaaS, SaaS), Public vs Private vs Hybrid cloud",
                "AWS Global Infrastructure: Regions, Availability Zones (AZs), Local Zones, Edge Locations",
                "AWS Management Console navigation, AWS Budgets, Cost Explorer, Free Tier limits"
            ]),
            ("Module 2: Identity & Access Management (IAM) & AWS CLI", [
                "IAM Users, User Groups, Policies (JSON structure: Effect, Action, Resource, Condition)",
                "IAM Roles for AWS Services, Instance Profiles, Cross-account access",
                "Multi-Factor Authentication (MFA), Password policies, Access Keys",
                "AWS CLI installation, configuration, AWS CloudShell, IAM Best Practices and Security Audit Tools"
            ]),
            ("Module 3: Compute Services (Amazon EC2)", [
                "Amazon EC2 introduction: Instance types (General Purpose, Compute, Memory, Storage Optimized)",
                "Amazon Machine Images (AMIs), Launching Linux & Windows instances, SSH/PuTTY & RDP access",
                "EC2 User Data bootstrap scripts for automated web server deployment",
                "EC2 Pricing models: On-Demand, Reserved, Spot Instances, Savings Plans, Dedicated Hosts"
            ]),
            ("Module 4: Storage Services (EBS, EFS & Amazon S3)", [
                "Amazon Elastic Block Store (EBS): Volume types (gp3, io2, st1, sc1), Snapshots, Encryption with KMS",
                "Amazon Elastic File System (EFS): Managed NFS for multi-EC2 shared storage",
                "Amazon Simple Storage Service (S3): Buckets, Objects, S3 Storage Classes (Standard, IA, Glacier, Deep Archive)",
                "S3 Versioning, Lifecycle Rules, S3 Bucket Policies, Cross-Region Replication, Static Website Hosting"
            ]),
            ("Module 5: Networking & Custom Virtual Private Cloud (VPC)", [
                "CIDR notation, IPv4 subnetting basics, Default vs Custom VPC",
                "Subnets: Public Subnets vs Private Subnets, Internet Gateways (IGW), Route Tables",
                "NAT Gateways vs NAT Instances for outbound private subnet connectivity",
                "Security Groups (Stateful) vs Network Access Control Lists - NACLs (Stateless)",
                "VPC Peering, VPC Flow Logs, Bastion Hosts / Jump Servers"
            ]),
            ("Module 6: High Availability, Load Balancing & Auto Scaling", [
                "Elastic Load Balancing (ELB): Application Load Balancer (ALB), Network Load Balancer (NLB)",
                "Target Groups, Health Checks, Path-based & Host-based routing, SSL/TLS certificate offloading",
                "Auto Scaling Groups (ASG): Launch Templates, Min/Max/Desired capacity, Scaling policies (Target tracking, Step, Simple scaling)"
            ]),
            ("Module 7: Relational & NoSQL Database Services", [
                "Amazon Relational Database Service (RDS): MySQL, PostgreSQL, Multi-AZ deployment for High Availability, Read Replicas",
                "Amazon Aurora: Architecture, High performance, Auto-scaling storage, Global Database",
                "Amazon DynamoDB: NoSQL key-value database, Partition keys, Sort keys, Global Tables"
            ]),
            ("Module 8: DNS, Caching & Content Delivery", [
                "Amazon Route 53: Public & Private Hosted Zones, Routing Policies (Simple, Weighted, Latency, Failover, Geolocation)",
                "Amazon CloudFront: Content Delivery Network (CDN), Edge locations, Origin Access Control (OAC), SSL integration",
                "Amazon ElastiCache: Redis and Memcached in-memory caching for database offloading"
            ]),
            ("Module 9: Serverless Computing & Application Integration", [
                "AWS Lambda: Serverless compute, Triggers, Execution role, Concurrency, Environment variables",
                "Amazon API Gateway: REST API and HTTP API integration with Lambda",
                "Application Messaging: Amazon SQS (Standard & FIFO queues), Amazon SNS (Publish/Subscribe pub-sub), EventBridge"
            ]),
            ("Module 10: Monitoring, Security & Well-Architected Framework", [
                "Monitoring: Amazon CloudWatch (Metrics, Alarms, Logs, Dashboards), AWS CloudTrail (API audit logging)",
                "Security: AWS Key Management Service (KMS), AWS WAF (Web Application Firewall), AWS Shield (DDoS protection)",
                "AWS Well-Architected Framework: 6 Pillars (Operational Excellence, Security, Reliability, Performance, Cost, Sustainability)"
            ])
        ],
        "projects": [
            "Highly Available, Multi-AZ Fault-Tolerant Web Application Architecture with ALB, Auto Scaling & RDS Multi-AZ",
            "Serverless Event-Driven Image Thumbnail Processing Pipeline using S3, Lambda, SNS, and DynamoDB",
            "Secure Corporate Hybrid Cloud VPC Architecture with Public/Private Subnets, NAT Gateways & Bastion Host"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized AWS Cloud Architect Certificate."
    },
    {
        "code": "CLOUD-SALESFORCE",
        "title": "Salesforce CRM Cloud (Administrator & Platform Developer Masterclass)",
        "field": "Cloud Computing",
        "duration_months": 3,
        "total_fee": Decimal("22000.00"),
        "source_url": "https://graphixtechnoservices.com/salesforce-course/",
        "overview": "Comprehensive Salesforce CRM training covering Salesforce Administrator and Platform Developer I curriculum. Master data modeling, security, flow automations, reports, Apex programming, SOQL, triggers, and Lightning Web Components (LWC).",
        "prerequisites": "Any graduate or software professional with basic programming or business logic concepts.",
        "software_covered": ["Salesforce Lightning Platform", "VS Code with Salesforce Extensions", "Salesforce CLI"],
        "modules": [
            ("Module 1: CRM Concepts & Salesforce Architecture", [
                "Customer Relationship Management (CRM) lifecycle: Lead to Opportunity to Cash",
                "Salesforce Architecture: Multi-tenant cloud, Metadata-driven platform, API-first architecture",
                "Standard Objects: Leads, Accounts, Contacts, Opportunities, Cases, Campaigns, Products, Pricebooks",
                "Lightning Experience interface navigation and Setup menu organization"
            ]),
            ("Module 2: Data Modeling & Schema Management", [
                "Custom Objects, Custom Fields (Text, Number, Currency, Date, Picklist, Multi-select, Formula fields, Roll-up Summary)",
                "Relationships: Lookup Relationships, Master-Detail Relationships, Many-to-Many (Junction Objects), External Lookups",
                "Schema Builder: Visual database design, Field dependencies, Custom Tabs creation"
            ]),
            ("Module 3: Security & Access Control Model", [
                "Multi-layer Security Model: Object-level, Field-level, Record-level security",
                "Object & Field Security: Profiles, Standard vs Custom Profiles, Permission Sets, Permission Set Groups",
                "Record-Level Security: Organization-Wide Defaults (OWD - Private, Public Read-Only, Public Read/Write)",
                "Role Hierarchy, Sharing Rules (Criteria-based, Owner-based), Manual Sharing, Public Groups"
            ]),
            ("Module 4: Business Logic Automation (Flows & Rules)", [
                "Validation Rules: Error conditions, RegEx formulas, Error message placement",
                "Salesforce Flows (The modern automation engine): Screen Flows, Record-Triggered Flows, Schedule-Triggered Flows, Auto-launched Flows",
                "Flow Elements: Assignment, Decision, Loop, Get Records, Create Records, Update Records, Delete Records",
                "Approval Processes: Step criteria, Approver assignment, Initial submission actions, Final approval/rejection actions"
            ]),
            ("Module 5: Reports & Dashboards Analytics", [
                "Report Formats: Tabular Reports, Summary Reports, Matrix Reports, Joined Reports",
                "Custom Report Types, Report Filters, Bucket Fields, Summary Formulas",
                "Interactive Dashboards: Chart types (Bar, Line, Donut, Gauge, Metric, Funnel), Dashboard filters, Scheduling and Subscriptions"
            ]),
            ("Module 6: Apex Programming (Platform Developer)", [
                "Apex Language Basics: Data types, Variables, Collections (List, Set, Map), Control flow statements",
                "SOQL (Salesforce Object Query Language) & SOSL (Salesforce Object Search Language): Queries, Relationships, Aggregate queries",
                "DML Operations (Insert, Update, Delete, Undelete, Upsert), Database class methods, Savepoints & Rollback",
                "Apex Triggers: Trigger events (before insert/update/delete, after insert/update/delete), Context variables (Trigger.new, Trigger.old, Trigger.isBefore, etc.)",
                "Trigger Frameworks & Best Practices: One trigger per object, Handler classes, Bulkification, Governor Limits",
                "Apex Unit Testing: @isTest, Test.startTest(), Test.stopTest(), System.assert, Achieving >75% test coverage"
            ]),
            ("Module 7: Lightning Web Components (LWC) & Deployment", [
                "Introduction to Lightning Web Components (LWC), Web Standards vs Aura components",
                "LWC Component Structure: HTML template, JavaScript controller, XML configuration metadata, CSS styles",
                "Data Binding, Conditional rendering, Iteration, Decorators (@api, @track, @wire)",
                "Wire Service to fetch data from Apex methods, Imperative Apex calls, Component communication (Custom Events)",
                "Salesforce DX (SFDX), VS Code integration, Scratch orgs, Sandboxes, Change Sets, and Production deployment"
            ])
        ],
        "projects": [
            "Coaching Institute Student Admission & Fee Installment Automation in Salesforce",
            "Customer Support Ticketing & Service Cloud Portal with SLA Milestone Automation",
            "Custom Course Enrollment Portal built with Lightning Web Components (LWC) and Apex Backend"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Salesforce Specialist Certificate."
    },
    {
        "code": "IT-DATA-SCIENCE-AI",
        "title": "Data Science, Machine Learning & Artificial Intelligence Masterclass",
        "field": "Data Science & AI/ML",
        "duration_months": 5,
        "total_fee": Decimal("32000.00"),
        "source_url": "https://graphixtechnoservices.com/data-science-machine-learning-ai/",
        "overview": "Comprehensive program in Data Science, Machine Learning, Deep Learning, and Artificial Intelligence. Covers mathematics, Python programming, Exploratory Data Analysis, predictive modeling with Scikit-learn, Neural Networks with TensorFlow/Keras, NLP, and model deployment.",
        "prerequisites": "Degree in Engineering, Computer Science, Statistics, Mathematics, or any quantitative discipline.",
        "software_covered": ["Python 3.11", "Jupyter Notebook", "NumPy", "Pandas", "Matplotlib / Seaborn", "Scikit-learn", "TensorFlow / Keras", "Streamlit"],
        "modules": [
            ("Module 1: Mathematics & Statistics for Data Science", [
                "Linear Algebra: Vectors, Matrices, Matrix operations, Eigenvalues, Eigenvectors, Dot product",
                "Calculus: Derivatives, Partial derivatives, Gradients, Gradient Descent optimization algorithm",
                "Descriptive Statistics: Mean, Median, Mode, Variance, Standard Deviation, Percentiles, Interquartile Range (IQR)",
                "Inferential Statistics: Probability distributions (Normal, Binomial, Poisson), Central Limit Theorem, Hypothesis Testing (Null vs Alternative, p-value, t-test, z-test, Chi-Square test, ANOVA)"
            ]),
            ("Module 2: Python for Data Science & Data Wrangling", [
                "Python programming fundamentals: Data types, Lists, Tuples, Dictionaries, Sets, Functions, List comprehensions",
                "NumPy: N-dimensional arrays, Array slicing, Broadcasting, Mathematical operations, Linear algebra module",
                "Pandas: Series and DataFrames, Data ingestion (CSV, Excel, SQL, JSON), Indexing, Filtering, Slicing",
                "Data Cleaning: Handling missing values (Imputation), Removing duplicates, Handling outliers (Z-score, IQR method)",
                "Data Transformation: Merging, Joining, Concatenating, Pivot tables, GroupBy aggregations, String and Datetime operations"
            ]),
            ("Module 3: Exploratory Data Analysis (EDA) & Visualization", [
                "Data Visualization with Matplotlib: Line plots, Bar charts, Histograms, Scatter plots, Subplots",
                "Advanced Visualization with Seaborn: Box plots, Violin plots, Heatmaps, Pairplots, Countplots, FacetGrid",
                "Feature Engineering: Handling categorical data (One-Hot Encoding, Label Encoding), Feature Scaling (StandardScaler, MinMaxScaler), Log transformation"
            ]),
            ("Module 4: Machine Learning - Supervised Learning", [
                "Machine Learning workflow: Train-Test split, Cross-Validation (K-Fold, Stratified K-Fold), Bias-Variance tradeoff",
                "Regression Algorithms: Simple & Multiple Linear Regression, Polynomial Regression, Regularization (Ridge L2, Lasso L1, ElasticNet)",
                "Regression Evaluation Metrics: Mean Absolute Error (MAE), Mean Squared Error (MSE), Root Mean Squared Error (RMSE), R-squared, Adjusted R-squared",
                "Classification Algorithms: Logistic Regression, K-Nearest Neighbors (KNN), Naive Bayes classifier, Support Vector Machines (SVM)",
                "Tree-based Models: Decision Trees (Gini impurity, Entropy, Information Gain, Pruning), Random Forest (Bagging, Feature importance), Gradient Boosting (GBM, XGBoost, LightGBM)",
                "Classification Metrics: Confusion Matrix, Accuracy, Precision, Recall, F1-Score, ROC-AUC curve"
            ]),
            ("Module 5: Machine Learning - Unsupervised Learning & Clustering", [
                "Clustering: K-Means Clustering, Elbow method, Silhouette score analysis, Hierarchical / Agglomerative Clustering, Dendrograms",
                "Dimensionality Reduction: Principal Component Analysis (PCA) - Variance ratio, Feature projection, t-SNE basics"
            ]),
            ("Module 6: Deep Learning & Artificial Neural Networks (ANN)", [
                "Biological Neuron vs Artificial Neuron, Perceptron model, Multi-Layer Perceptron (MLP)",
                "Neural Network Architecture: Input layer, Hidden layers, Output layer, Weights, Biases, Activation Functions (Sigmoid, Tanh, ReLU, LeakyReLU, Softmax)",
                "Training Neural Networks: Cost function, Forward propagation, Backpropagation, Optimizers (SGD, Momentum, RMSprop, Adam)",
                "Overfitting solutions: Dropout layers, Early Stopping, L1/L2 regularization",
                "TensorFlow & Keras framework: Building Sequential & Functional models, Model compilation, Model training, Evaluation"
            ]),
            ("Module 7: Natural Language Processing (NLP) & Model Deployment", [
                "NLP Fundamentals: Text preprocessing, Tokenization, Stopword removal, Stemming vs Lemmatization (NLTK, spaCy)",
                "Text Vectorization: Bag of Words (CountVectorizer), TF-IDF (Term Frequency - Inverse Document Frequency), Word Embeddings (Word2Vec basics)",
                "Sentiment Analysis & Text Classification using Naive Bayes and Logistic Regression",
                "Model Deployment: Saving models with Pickle / Joblib, Building interactive web application UI with Streamlit, Containerization with Docker"
            ])
        ],
        "projects": [
            "Customer Churn Prediction and Risk Classification System using Random Forest and XGBoost",
            "Medical Disease Diagnosis Prediction Web Application using Machine Learning & Streamlit",
            "Real-Time Sentiment Analysis Tool for Social Media Product Reviews using Natural Language Processing"
        ],
        "certification": "Central Government ISO Certified & BECIL Authorized Data Science & AI Certificate."
    },

    # =========================================================================
    # DISCIPLINE 5: PROFESSIONAL DEVELOPMENT & CORPORATE READINESS
    # =========================================================================
    {
        "code": "PRO-COMM-TRAINING",
        "title": "Corporate Communication & Personality Development Programme",
        "field": None,
        "duration_months": 1.5,
        "total_fee": Decimal("8000.00"),
        "source_url": "https://graphixtechnoservices.com/communication-training/",
        "overview": "Placement-focused communication and professional personality development training designed for engineering freshers, job seekers, and working professionals. Covers spoken English fluency, business correspondence, group discussions, public presentations, and technical/HR interview mastery.",
        "prerequisites": "Open to all students, job aspirants, and professionals looking to enhance their corporate communication skills.",
        "software_covered": ["MS PowerPoint", "Zoom / Google Meet Professional Etiquette", "LinkedIn"],
        "modules": [
            ("Module 1: Spoken English & Accent Neutralization", [
                "Grammar Refinement: Sentence structures, Tenses in corporate context, Common grammatical errors to eliminate",
                "Pronunciation & Phonetics: Neutral accent development, Syllable stress, Intonation, Mother Tongue Influence (MTI) reduction",
                "Vocabulary Building: Corporate terminology, Collocations, Phrasal verbs, Active listening exercises"
            ]),
            ("Module 2: Professional Business Writing & Email Etiquette", [
                "Email Etiquette: Subject lines, Professional salutations, Tone (Formal vs Informal), Clear action items, Sign-offs",
                "Corporate Communication: Writing memos, Project status reports, Professional inquiries, Following up politely",
                "Modern Digital Communication: Professional messaging on Slack/Teams, WhatsApp business etiquette"
            ]),
            ("Module 3: Public Speaking & Presentation Skills", [
                "Overcoming Glossophobia (Fear of public speaking), Voice modulation, Breath control, Pacing",
                "Non-verbal Communication: Eye contact, Confident body posture, Hand gestures, Facial expressions",
                "Designing High-Impact Presentations: 10/20/30 rule, Storytelling techniques, Slide design principles in PowerPoint, Delivering technical presentations"
            ]),
            ("Module 4: Group Discussions (GD) Mastery", [
                "Group Discussion Dynamics: What recruiters look for in GDs (Content, Leadership, Communication, Team spirit)",
                "GD Strategies: Initiating discussions, Entering effectively, Supporting points with data, Handling interruptions, Summarizing",
                "Handling various GD topics: Current affairs, Abstract topics, Technical trends, Case study-based GDs",
                "Body language, Active listening, and Professional disagreement etiquette during GDs"
            ]),
            ("Module 5: Resume Building & Professional LinkedIn Branding", [
                "ATS-Compliant Resume Writing: Formatting, Action verbs, Highlighting technical CAD/IT projects, Objective vs Summary statements",
                "Crafting Tailored Cover Letters for engineering & IT job applications",
                "LinkedIn Optimization: Headline, About section, Showcasing projects and certifications, Professional networking strategies"
            ]),
            ("Module 6: Technical & HR Interview Preparation", [
                "Interview Preparation: Researching the company, Dressing sense, Punctuality, Virtual interview setup (Lighting, Audio, Background)",
                "Self-Introduction Mastery: 'Tell me about yourself' pitch tailored for engineering freshers vs experienced candidates",
                "Behavioral Questions using STAR Methodology (Situation, Task, Action, Result)",
                "Handling Difficult & Tricky Questions (Strengths/Weaknesses, Gaps in education, Conflict with team members)",
                "Salary Negotiation tactics and asking smart questions to interviewers",
                "Mock Interviews: 1-on-1 simulated interviews with video recording and individualized feedback reports"
            ])
        ],
        "projects": [
            "Video-Recorded Mock Technical & HR Interview Session with Detailed Performance Scorecard",
            "Live Group Discussion Simulation Round on Contemporary Technology & Engineering Trends",
            "Individual 10-Minute Corporate Technical Presentation with Slide Deck & Peer Evaluation"
        ],
        "certification": "Central Government ISO Certification & BECIL Authorized Communication Training Certificate."
    }
]


def generate_markdown_catalog():
    """Generates the comprehensive standalone Markdown document for all courses."""
    doc_lines = []
    doc_lines.append("# Graphix Techno Services - Master Course Syllabus & Curriculum Catalogue")
    doc_lines.append("\n> **Authorized Central Government CAD/CAM/CAE Training Institute**")
    doc_lines.append("> Certified under ISO 9001:2015 & BECIL (Govt. of India Enterprise under Ministry of Information & Broadcasting)")
    doc_lines.append("> Website: [https://graphixtechnoservices.com/](https://graphixtechnoservices.com/)\n")
    doc_lines.append("## Executive Summary")
    doc_lines.append(
        "This master catalog comprises the complete, industry-standardized course syllabuses offered by Graphix Techno Services. "
        "Every syllabus has been enriched with full module breakdowns, software versions, prerequisites, real-world capstone projects, "
        "and national/international engineering codes (ASME, ISO, ASHRAE, IS, IEEE, AWS).\n"
    )
    doc_lines.append("---")
    doc_lines.append("## Table of Contents")
    for idx, c in enumerate(COURSE_DATA, start=1):
        doc_lines.append(f"{idx}. [{c['title']} (`{c['code']}`)](#{c['code'].lower()})")
    doc_lines.append("\n---\n")

    for c in COURSE_DATA:
        doc_lines.append(f"<a id='{c['code'].lower()}'></a>")
        doc_lines.append(f"# {c['title']}")
        doc_lines.append(f"- **Course Code:** `{c['code']}`")
        doc_lines.append(f"- **Engineering Discipline:** {c['field'] or 'Professional Development'}")
        doc_lines.append(f"- **Duration:** {c['duration_months']} Months (Approx. {c['duration_months'] * 40} Hours)")
        doc_lines.append(f"- **Estimated Course Fee:** INR {c['total_fee']:,.2f}")
        doc_lines.append(f"- **Source Reference:** [{c['source_url']}]({c['source_url']})")
        doc_lines.append(f"- **Certification:** {c['certification']}\n")

        doc_lines.append("### Course Overview")
        doc_lines.append(c["overview"] + "\n")

        doc_lines.append("### Target Audience & Prerequisites")
        doc_lines.append(c["prerequisites"] + "\n")

        doc_lines.append("### Software Tools & Technologies Covered")
        for s in c["software_covered"]:
            doc_lines.append(f"- {s}")
        doc_lines.append("")

        doc_lines.append("### Detailed Module-by-Module Curriculum")
        for mod_title, topics in c["modules"]:
            doc_lines.append(f"#### {mod_title}")
            for t in topics:
                doc_lines.append(f"- {t}")
            doc_lines.append("")

        doc_lines.append("### Industrial Hands-on Capstone Projects")
        for p in c["projects"]:
            doc_lines.append(f"1. **{p}**")
        doc_lines.append("")
        doc_lines.append("---\n")

    content = "\n".join(doc_lines)
    out_path = os.path.join(BASE_DIR, "GRAPHIX_TECHNO_SERVICES_COURSE_SYLLABUS_CATALOGUE.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated master markdown catalog at: {out_path} ({len(content)} chars)")
    return content


def run():
    print("=" * 70)
    print("STARTING GRAPHIX TECHNO SERVICES COURSE SEED & INGESTION")
    print("=" * 70)

    # 1. Generate master markdown catalog
    catalog_markdown = generate_markdown_catalog()

    with transaction.atomic():
        # 2. Ingest or update Course models
        print("\n--> Seeding Course records in academics.models.Course...")
        created_courses = 0
        updated_courses = 0
        course_map = {}

        for cdata in COURSE_DATA:
            course, created = Course.objects.update_or_create(
                code=cdata["code"],
                defaults={
                    "title": cdata["title"],
                    "description": cdata["overview"],
                    "duration_months": cdata["duration_months"],
                    "total_fee": cdata["total_fee"],
                    "field_of_engineering": cdata["field"],
                }
            )
            course_map[cdata["code"]] = course
            if created:
                created_courses += 1
            else:
                updated_courses += 1

        print(f"Courses processed: {created_courses} created, {updated_courses} updated. Total courses: {len(course_map)}")

        # 3. Create or update KnowledgeDocument records
        print("\n--> Ingesting KnowledgeDocument records in rag.models.KnowledgeDocument...")
        total_chunks = 0
        indexed_docs = 0

        # Ingest Master Catalogue Document
        master_doc, _ = KnowledgeDocument.objects.update_or_create(
            title="Graphix Techno Services - Master Course Syllabus & Curriculum Catalogue",
            category="COURSE_CATALOGUE",
            defaults={
                "content": catalog_markdown,
                "source_url": "https://graphixtechnoservices.com/courses/",
                "is_published": True,
                "metadata_json": {
                    "doc_type": "MASTER_CATALOGUE",
                    "total_courses": len(COURSE_DATA),
                    "institute": "Graphix Techno Services",
                    "certifications": "ISO 9001:2015 & BECIL Central Government"
                }
            }
        )
        chunks = IngestionService.index_document(master_doc)
        total_chunks += chunks
        indexed_docs += 1
        print(f"Indexed Master Catalogue: {chunks} chunks")

        # Ingest individual course study guide / syllabus documents
        for cdata in COURSE_DATA:
            course_obj = course_map[cdata["code"]]
            
            # Format course specific markdown syllabus
            mod_text = []
            for mod_title, topics in cdata["modules"]:
                mod_text.append(f"### {mod_title}")
                for t in topics:
                    mod_text.append(f"- {t}")
                mod_text.append("")
                
            proj_text = "\n".join(f"{i+1}. {p}" for i, p in enumerate(cdata["projects"]))
            soft_text = ", ".join(cdata["software_covered"])

            syllabus_content = f"""
# Course Syllabus: {cdata['title']}
- **Course Code:** `{cdata['code']}`
- **Discipline:** {cdata['field'] or 'Professional Development'}
- **Duration:** {cdata['duration_months']} Months
- **Fee:** INR {cdata['total_fee']:,.2f}
- **Software & Tools:** {soft_text}
- **Official Website:** {cdata['source_url']}
- **Certification:** {cdata['certification']}

## Course Overview
{cdata['overview']}

## Prerequisites & Eligibility
{cdata['prerequisites']}

## Detailed Curriculum Modules
{chr(10).join(mod_text)}

## Industrial Projects & Practical Applications
{proj_text}

## Placement & Training Highlights
- Central Government ISO Certification & BECIL Authorized Credential.
- 100% Placement Assistance with resume preparation and campus interview drives.
- Lifetime student membership & free revision batches allowed.
- Hands-on practical training with industrial CAD/CAM/CAE/Full-Stack live projects.
""".strip()

            kdoc, _ = KnowledgeDocument.objects.update_or_create(
                title=f"Syllabus: {cdata['title']} ({cdata['code']})",
                category="STUDY_GUIDE",
                defaults={
                    "content": syllabus_content,
                    "source_url": cdata["source_url"],
                    "is_published": True,
                    "metadata_json": {
                        "course_id": str(course_obj.id),
                        "code": cdata["code"],
                        "field": cdata["field"],
                        "duration_months": cdata["duration_months"],
                        "total_fee": float(cdata["total_fee"]),
                        "tools": cdata["software_covered"]
                    }
                }
            )
            
            c_count = IngestionService.index_document(kdoc)
            total_chunks += c_count
            indexed_docs += 1
            print(f"Indexed: {cdata['code']} - {cdata['title'][:35]}... ({c_count} chunks)")

    print("\n" + "=" * 70)
    print(f"INGESTION COMPLETED SUCCESSFULLY!")
    print(f"Total Knowledge Documents Indexed: {indexed_docs}")
    print(f"Total Vector Chunks Generated: {total_chunks}")
    print("=" * 70)


if __name__ == "__main__":
    run()
