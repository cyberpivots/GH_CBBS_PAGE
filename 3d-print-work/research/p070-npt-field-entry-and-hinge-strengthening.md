# P070 3/4 NPT Field Entry And Hinge Strengthening Findings

Truth state: internal review.

This note records the source basis for the next strengthening pass on the
`p070_hinged_wall_enclosure` and
`p070_heltec_outdoor_controller_enclosure` CAD assemblies. It is not public
product copy and does not approve strength, ingress, runtime, RF, cable
retention, or field service claims.

## Verified Inputs

- The selected field-entry reference is LAPP article 53016150,
  SKINTOP STR NPT 3/4, silver gray. LAPP's current product page identifies the
  thread as NPT 3/4, the clamping range as 0.354-0.63 in, and the spanner size
  as 1.299 in.
- The LAPP SKINTOP ST NPT / STR NPT data sheet lists the STR NPT 3/4 row with
  SW 33 mm, ØA 36.2 mm, C 43.5 mm, D 53.0 mm, ØF 15 mm, clamping range
  9-16 mm, and article 53016150.
- ANSI/ASME B1.20.1 NPT reference data identifies 3/4 NPT as 14 TPI with
  nominal 1.050 in OD, 1:16 taper on diameter, and a 60 degree thread form.
  The generated thread is a printed prototype derived from those values, not a
  certified pipe-thread feature.
- CadQuery 2.7 exposes `Wire.makeHelix` and sweep APIs, but local checks showed
  conical swept thread cutters were fragile and slow in this assembly. The CAD
  generator therefore uses segmented helical internal ridges on a tapered bore.
  This keeps STEP/STL export and watertight mesh checks reliable while still
  producing a physical printed thread prototype that must be coupon-tested.
- The repo's Heltec V2 and Pololu regulator records provide board envelopes but
  not verified screw-hole coordinates. Hardware placement may use rails, stops,
  retainers, and keepout metadata only.

## CAD Rules

- Keep the existing 5-knuckle symmetric hinge, pin diameter, bore diameter,
  print flat, and end chamfer.
- Add more substantial hinge saddle pads, hinge-side backer rails, and gusset
  webs without increasing the P070 rear-panel or front-door X/Y footprint.
- Keep tray-owned reinforcement tied to tray-owned knuckles and door-owned
  reinforcement tied to door-owned knuckles. Reinforcement must not bridge
  opposing hinge owners.
- Put the 3/4 NPT field-entry boss on the separate rear battery/electronics pod,
  separated from the SMA/RF route. Do not place it on the tight P070 door or
  rear-panel plate.
- Route field wiring with non-claiming channels, rails, and clip features from
  the 3/4 NPT entry toward the regulator bay; keep the RF pigtail route
  separate from the main field-wire trunk.
- Add a 3/4 NPT thread-fit coupon with multiple radial-clearance variants before
  relying on the enclosure boss.

## Remaining Blockers

- Print the thread-fit coupon in the intended ASA profile and test the actual
  LAPP 53016150 gland before accepting the enclosure boss.
- Measure cable count, cable outside diameter, bend radius, nut/washer stack,
  panel thickness, and service-loop space.
- Print the reinforced hinge parts in ASA and validate hinge cycling, pin
  retention, crack initiation, and door service handling.
- Measure the actual Heltec/regulator hardware before adding official screw
  holes, heat-set insert holes, or fastener claims.
- Validate heat, RF, cable retention, service access, condensation behavior, and
  installed handling before any release review.

## Sources

- LAPP SKINTOP STR NPT 3/4 product page for article 53016150: https://www.lapp.com/en_US/us/skintop-st-npt/skintop-str-npt/p/53016150
- LAPP SKINTOP ST NPT / STR NPT data sheet: https://imager.lapp.com/e/lapp/KzjVn7imdUf9vJ1LttiCMA~~/DB53016010EN.pdf
- Engineering ToolBox ANSI/ASME B1.20.1 NPT reference table: https://www.engineeringtoolbox.com/npt-national-pipe-taper-threads-d_750.html
- CadQuery class reference: https://cadquery.readthedocs.io/en/latest/classreference.html
- P070 structural strengthening findings: 3d-print-work/research/p070-structural-strengthening-findings.md
- P070 Heltec outdoor power/RF findings: 3d-print-work/research/p070-heltec-outdoor-power-rf-findings.md
