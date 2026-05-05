# Rapid Prototyping Method

Truth state: internal review / concept.

This executes Phases 3, 4, and 5 of `research-plan.md`. It defines the default method for moving from verified hardware to printable prototypes.

## Design Rules From Research

- Model for the printer process, not just the nominal geometry. Prusa guidance highlights support avoidance, print orientation, split models, chamfers for assembly, nozzle/perimeter limits, and tolerance tuning.
- For common FFF workflows, use wall thicknesses that map cleanly to nozzle extrusion widths. Prusa's example for a 0.4 mm nozzle gives approximate wall widths of 0.45 mm per perimeter, so enclosure walls and bosses should be designed as intentional perimeter multiples rather than arbitrary thin shells.
- Do not rely on zero-clearance fits. Prusa explicitly notes that fitted parts need tolerance and that the right value depends on printer, material, geometry, and settings.
- Use critical-section test prints before full-size enclosures. UltiMaker recommends test prints for critical sections and systematic documentation of test results.
- Use split multi-part bodies when orientation, strength, surface finish, or support reduction demands it.
- Keep slicer project files for print reproducibility. Prusa documents 3MF project files as containing objects, settings, modifiers, and parameters.

Sources:
- https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135/
- https://ultimaker.com/learn/how-to-design-for-3d-printing-a-comprehensive-guide-to-creating-3d-printable-designs/
- https://help.prusa3d.com/article/saving-projects-as-3mf_1773

## Default Prototype Sequence

1. Source capture
   - Confirm exact model/revision.
   - Save official drawings or datasheet links in `research/sources.md`.
   - Measure actual hardware using `measurement-checklist.md`.

2. Bounding model
   - Create a board/display bounding box with mounting holes, connector keepouts, display opening, cable envelopes, and antenna zones.
   - Mark unverified dimensions in the CAD notes.

3. Coupon prints
   - Print small tests for screw bosses, heat-set insert holes, snap tabs, living clearance, cable clips, gasket grooves, display window overlap, label engraving, and logo embossing.
   - For rugged/outdoor-facing work, print wall-section, gasket-flange,
     drip-lip seam, cable-entry boss, and reinforced mount-tab coupons before
     full enclosure geometry.
   - Record results in `prints/prototype-log-template.md`.

4. Fit frame
   - Print an open tray or flat bezel frame using only the critical fit features.
   - Install real board/display/cables/antenna and mark collisions.

5. First enclosure
   - Print a basic enclosure with service openings and fasteners.
   - Avoid cosmetic detail until fit, cable routing, and assembly are proven.

6. Functional prototype
   - Add ventilation, antenna strain relief, mounting features, labels, and display/lens refinement.
   - Run validation checklists before calling a model ready for field handling.

## Material Strategy

- PLA: fit checks, dimension coupons, and fast low-risk visual prototypes.
- PETG: functional indoor prototypes where toughness and higher temperature resistance than PLA are useful.
- ASA: outdoor-facing or higher-temperature prototypes only when the printer, ventilation, and enclosure workflow support it. Prusa describes ASA as suitable for outdoor use and technical parts due to UV and temperature resistance, but also notes warping and fume concerns.
- PC-class materials: defer until printer capability and safety controls are known.

Do not claim weather resistance, UV lifetime, heat performance, or impact resistance based on material name alone. Validate the printed part in the intended configuration.

Source:
- https://help.prusa3d.com/article/asa_1809

## Electronics-Specific Constraints

- Do not trap heat-generating boards without a measured thermal path.
- Keep service access for programming, reset, power, storage, and emergency removal.
- Keep antenna geometry and cable strain relief visible in the prototype notes.
- Do not use metal inserts, screws, foil, or magnetic mounts near antennas without RF testing.
- Avoid tight cable bends at USB, battery, antenna, and display harness exits.
- Use actual cables during every fit test, not just connector dimensions.

## Outdoor-Facing Constraints

- Treat rugged/outdoor model names as prototype intent only.
- Use `environmental_context.rating_claims` only after the exact hardware,
  material, gasket/cable/vent hardware, and validation plan are known.
- Keep seam, gasket, cable-entry, and vent geometry in coupons until their
  behavior is physically checked.
- Account for condensation and pressure changes before sealing a case tightly.
- Keep service access and thermal behavior ahead of cosmetic rugged styling.

## Documentation Required For Each Prototype

- Concept family and prototype revision.
- Hardware model/revision measured.
- Source CAD file path.
- Exported STEP/STL/3MF paths.
- Material, nozzle, layer height, wall count, infill, orientation, supports, and slicer.
- Fit result: pass, fail, partial, or reprint required.
- Known risks and next changes.
