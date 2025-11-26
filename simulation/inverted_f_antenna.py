"""
INVERTED F ANTENNA DESIGN

This design models an inverted F antenna (IFA) on a dielectric substrate for a 868 MHz LoRa application.
Based on Texas Instruments Design Note DN023: https://www.ti.com/lit/an/swra228c/swra228c.pdf

  ↑  +-------------------------------+      +----------------+  ↑
  |  |                               |←-L5-→|                |  |
  |  |    +-------+      +------+    |      |    +------+    |  |
  |  |    |       |      |      |    |   ↑  |    |      |    |  |
  |  |    |←-L2--→|      |←-L3-→|    |   |  |    |←-L5-→|    |  |
  |  |    |       |      |      |    |  L4  |    |      |    |  |
  |  |    |       |      |      |    |   |  |    |      |    |  L6
 L1  |    |       |      |      |    |   ↓  |    |      |    |  |
  |  |    |       |      |      |    +------+    |      |    |  |
  |  |    |       |      |      |                |      |    |  |
  |  |    |       |      |      +----------------+      |    |  |
  |  |    |       |      |                              |    |  |
  |  |    |       |      |                              +----+  ↓
  |  |    |       |      |                              ←-W--→
  ↓  +----+       +------+      |                       |
     ←-W--→       ←--W2--→      |--------- xN ----------|
"""

import emerge as em
import numpy as np
from emerge.plot import plot_ff, plot_ff_polar, plot_sp, smith


def main():
    # --- Unit and simulation parameters --------------------------------------
    mm = 0.001  # meters per millimeter
    # Refined frequency range for antenna resonance around 868 MHz
    f1 = 670e6  # [Hz] start frequency
    f2 = 1070e6  # [Hz] stop frequency

    # --- Antenna geometry dimensions -----------------------------------------
    W_feed = 2  # [mm] feed line width (W2)
    L_feed = 25  # [mm] feed length (L1)
    W_ant = 1  # [mm] antenna line width (W)
    L_ant_end = 2  # [mm] antenna line end length (L6)
    L_feed_to_short = 1  # [mm] length between feed line and shorting (ground) line (L2)
    L_feed_to_ant = 3  # [mm] length between feed line and antenna line (L3)

    # 1 zigzag section dimensions
    D_zigzag = 10  # [mm] vertical depth of zigzag (L4)
    L_zigzag = L_feed_to_ant  # [mm] horizontal length of zigzag U shape (L5)
    N_zigzags = 3  # number of zigzag sections

    # If thickness is different than 0.8 mm of the design note, L6 should be adjusted
    th = 1.51  # [mm] substrate thickness
    pcb_margin = (6, 6, 6, 6 * 8)  # [mm] margin between traces and PCB edge (left, top, right, bottom)
    margin = 50 * mm  # [mm] margin around PCB for air box

    # --- Create simulation object --------------------------------------------
    model = em.Simulation("IFA", loglevel="INFO")

    # --- Create PCB antenna geometry -----------------------------------------
    pcbl = em.geo.PCB(thickness=th, unit=mm, material=em.lib.DIEL_FR4)

    # Create the feed line
    pcbl.new(W_ant / 2 + L_feed_to_short + W_feed / 2, 0, W_feed, (0, 1)).store("p1").straight(L_feed)
    # Create the inverted F antenna
    ant = (
        pcbl.new(0, -0.5, W_ant, (0, 1))
        .short()  # via to ground plane
        .straight(L_feed - W_ant + 0.5)
        .turn(90, corner_type="square")
        .straight(L_feed_to_short + W_feed + L_feed_to_ant)
        .turn(90, corner_type="square")
    )
    for _ in range(max(N_zigzags, 0)):
        ant = (
            ant.straight(D_zigzag)
            .turn(-90, corner_type="square")
            .straight(L_zigzag)
            .turn(-90, corner_type="square")
            .straight(D_zigzag)
            .turn(90, corner_type="square")
            .straight(L_zigzag)
            .turn(90, corner_type="square")
        )
    ant.straight(L_ant_end).store("p2")

    x0, y0, z0 = pcbl.origin

    # Compile the PCB antenna geometry
    ant_trace = pcbl.compile_paths(merge=True)
    # Add margins between traces and PCB bounding box
    pcbl.determine_bounds(*pcb_margin)

    # Create ground plane on bottom and top side of PCB
    ground_bottom = em.geo.XYPlate(
        pcbl.width * mm,  # type: ignore
        -pcb_margin[3] * mm - 0.5 * mm,  # type: ignore
        (x0 * mm - pcb_margin[0] * mm - W_ant * mm / 2, y0 * mm, pcbl.z(1) * mm),
    ).set_material(em.lib.COPPER)

    # ground_top = em.geo.XYPlate(
    #     pcbl.width * mm,  # type: ignore
    #     -pcb_margin[3] * mm - 0.5 * mm,  # type: ignore
    #     (x0 * mm - pcb_margin[0] * mm - W_ant * mm / 2, y0 * mm, pcbl.z(2) * mm),
    # )
    # feed_cutout = em.geo.XYPlate(
    #     1.5 * W_feed * mm,
    #     -pcb_margin[3] * mm - 0.5 * mm,
    #     (x0 * mm + W_ant * mm / 2 + L_feed_to_short * mm - 0.25 * W_feed * mm, y0 * mm, pcbl.z(2) * mm),
    # )
    # ground_top = em.geo.remove(ground_top, feed_cutout).set_material(em.lib.COPPER)

    # Generate the PCB dielectric geometry
    dielectric = pcbl.generate_pcb(merge=True)
    via = pcbl.generate_vias()

    # Generate air box around the PCB
    air = em.geo.Box(
        pcbl.width * mm + 2 * margin,  # type: ignore
        pcbl.length * mm + 2 * margin,  # type: ignore
        2 * margin,
        (
            x0 * mm - pcb_margin[0] * mm - margin,
            y0 * mm - margin - pcb_margin[3] * mm,
            z0 * mm - margin,
        ),
    )

    # Create port at the feed line start
    lumped_port = pcbl.lumped_port(pcbl.load("p1"))

    # --- Assign simulation settings ------------------------------------------
    model.mw.set_resolution(0.2)
    # Frequency sweep across the resonance
    model.mw.set_frequency_range(f1, f2, 11)

    # --- Combine geometry into simulation ------------------------------------
    model.commit_geometry()
    model.mesher.set_boundary_size(ant_trace, 2 * mm, growth_rate=5)

    # --- Generate mesh and preview -------------------------------------------
    model.generate_mesh()
    model.view(selections=[lumped_port], plot_mesh=True, volume_mesh=False)  # type: ignore

    # --- Boundary conditions ------------------------------------------------
    # Define modal port with specified orientation and impedance
    port_bc = model.mw.bc.LumpedPort(lumped_port, 1, Z0=50)
    model.mw.bc.AbsorbingBoundary(air.outside())

    # --- Run frequency-domain solver ----------------------------------------
    model.set_solver(em.EMSolver.CUDSS)
    data = model.mw.run_sweep()

    # --- Post-process S-parameters ------------------------------------------
    freqs = data.scalar.grid.freq
    freq_dense = data.scalar.grid.dense_f(1001)
    S11 = data.scalar.grid.model_S(1, 1, freq_dense)  # reflection coefficient
    plot_sp(freq_dense, [S11], labels=["S11"])  # plot loss in dB
    smith(S11, f=freq_dense, labels="S11")  # Smith chart of S11

    # --- Far-field radiation pattern ----------------------------------------
    # Extract 2D cut at phi=0 plane and plot E-field magnitude
    ff1 = data.field.find(freq=868e6).farfield_2d((0, 0, 1), (1, 0, 0), air.outside())
    ff2 = data.field.find(freq=868e6).farfield_2d((0, 0, 1), (0, 1, 0), air.outside())

    plot_ff(
        ff1.ang * 180 / np.pi,  # type: ignore
        [ff1.normE / em.lib.EISO, ff2.normE / em.lib.EISO],
        dB=True,
        ylabel="Gain [dBi]",
    )  # linear plot vs theta
    plot_ff_polar(
        ff1.ang,  # type: ignore
        [ff1.normE / em.lib.EISO, ff2.normE / em.lib.EISO],
        dB=True,
        dBfloor=-20,
        title="Far-field polar plot of E-field magnitude vs angle",
    )  # polar plot of radiation

    # --- 3D visualization ---------------------------------------------------
    model.display.add_objects(*model.all_geos())
    model.display.add_surf(
        *data.field.find(freq=868e6).cutplane(ds=1 * mm, z=-th / 2 * mm).scalar("Ey"),
        symmetrize=True,
        _fieldname="Ey",
    )
    model.display.show()

    # --- 3D radiation visualization -----------------------------------------
    ff3d = data.field.find(freq=868e6).farfield_3d(air.outside())
    surf = ff3d.surfplot(
        "normE",
        dB=False,
        rmax=40 * mm,
        offset=((pcbl.width * mm - 2 * pcb_margin[0] * mm) / 2, (L_feed + D_zigzag) / 2 * mm, 0),  # type: ignore
    )

    model.display.add_objects(*model.all_geos())
    model.display.add_surf(*surf, opacity=0.9, _fieldname="Far-Field |E|")
    model.display.show()


if __name__ == "__main__":
    main()
