from __future__ import annotations

import numpy as np


class Replay:
    """Verifier implementation: ragged factors, sparse processing, batched histories."""

    def __init__(self, model):
        self.model = model
        self.count = model["node_count"]
        self.zone_count = model["zone_count"]
        self.zones = np.array(model["zone"])
        self.species = np.array(model["chemistry"])
        self.offsets = np.cumsum([0] + [len(factor["nodes"]) for factor in model["factors"]])
        self.nodes = np.concatenate([factor["nodes"] for factor in model["factors"]])
        self.signs = np.concatenate([factor["signs"] for factor in model["factors"]])
        self.weights = np.array([factor["weight"] for factor in model["factors"]])
        self.channels = np.array([factor["channel"] for factor in model["factors"]])
        self.sources = np.repeat(np.arange(len(self.weights)), np.diff(self.offsets))
        self.process_matrix = np.eye(3 * self.zone_count)
        coupling = model["constants"]["process_laplacian"] * np.array(model["processing_mix"])
        for first, second in model["zone_edges"]:
            first_axes, second_axes = np.arange(3 * first, 3 * first + 3), np.arange(3 * second, 3 * second + 3)
            self.process_matrix[np.ix_(first_axes, first_axes)] += coupling
            self.process_matrix[np.ix_(second_axes, second_axes)] += coupling
            self.process_matrix[np.ix_(first_axes, second_axes)] -= coupling
            self.process_matrix[np.ix_(second_axes, first_axes)] -= coupling
        self.contact_nodes = np.array([contact["nodes"] for contact in model["contacts"]])
        self.texture = np.array([contact["texture"] for contact in model["contacts"]])

    def native_state(self, orientation, controls):
        sums = np.add.reduceat(orientation[self.nodes] * self.signs, self.offsets[:-1])
        faults = np.abs(sums) == np.diff(self.offsets)
        blocked = np.zeros((5, self.count))
        channels = np.where(self.channels < 0, 0, self.channels + 1)
        np.add.at(blocked, (channels[self.sources], self.nodes), (faults * self.weights)[self.sources])
        target = np.array(self.model["processing_bias"], dtype=float)
        contact_products = orientation[self.contact_nodes[:, 0]] * orientation[self.contact_nodes[:, 1]]
        for endpoint in (0, 1):
            assigned_zone = self.zones[self.contact_nodes[:, endpoint]]
            zone_degrees = np.bincount(assigned_zone, minlength=self.zone_count)
            aggregated = np.zeros((self.zone_count, 3))
            np.add.at(aggregated, assigned_zone, contact_products[:, None] * self.texture)
            target += 0.3 * aggregated / zone_degrees[:, None]
        target -= target.mean(axis=0)
        residual = (self.process_matrix @ controls.ravel()).reshape(self.zone_count, 3) - target
        strain = np.linalg.norm(residual, axis=1)[self.zones] / np.sqrt(3.0)
        return {"faults": faults, "blocked": blocked, "residual": residual, "strain": strain}

    def scenarios(self, native, scenarios):
        families = np.array([scenario["family"] for scenario in scenarios], dtype=int)
        coordinate = np.array([scenario["coordinates"] for scenario in scenarios])
        thermal, flux, mass, cycle = coordinate.T
        base_temperature = 338.0 + np.where(families == 0, 32.0, 6.0) * thermal
        base_flux = 1.0 + np.where(families == 1, 0.55, 0.12) * flux
        isotope_mass = 1.6 + np.where(families == 2, 0.55, 0.12) * mass
        durations = 68.0 + np.where(families == 3, 12.0, 3.0) * cycle
        amplitudes = np.array(self.model["intervention_mix"])[np.maximum(families, 0)] * (0.65 + 0.35 * np.abs(coordinate))
        amplitudes[families == -1] = 0.0
        load = native["blocked"][0][None, :] + amplitudes @ native["blocked"][1:]
        blockade = 1.0 - np.exp(-load)
        strain = native["strain"][None, :]
        memory_retention = np.array(self.model["memory_retention"])[None, :]
        release_base = np.array(self.model["release_barrier_eV"])[None, :]
        retention_base = np.array(self.model["retention_barrier_eV"])[None, :]
        constants = self.model["constants"]
        yields = []
        for stages in ((-0.8, -0.25, 0.4, 0.9), (0.9, 0.4, -0.25, -0.8)):
            memory = np.zeros_like(blockade)
            release_hazard, retention_hazard = np.zeros_like(blockade), np.zeros_like(blockade)
            for stage in stages:
                temperature = base_temperature + stage * (7.0 + 2.0 * cycle)
                incident_flux = base_flux * (1.0 + 0.12 * stage)
                drive = 0.20 * incident_flux[:, None] + 0.10 * isotope_mass[:, None] + 0.28 * blockade + 0.35 * strain + 0.06 * (stage + 1.0)
                memory = memory * memory_retention + drive * (1.0 - memory_retention)
                release_energy = (release_base + constants["obstruction_barrier_eV"] * blockade
                                  + constants["strain_barrier_eV"] * strain + constants["memory_barrier_eV"] * memory
                                  + 0.006 * mass[:, None] - 0.004 * flux[:, None])
                retention_energy = retention_base - 0.12 * blockade - 0.045 * strain - 0.018 * memory
                prefactor = constants["attempt_rate_s"] * incident_flux / np.sqrt(isotope_mass)
                thermal_energy = constants["boltzmann_eV_K"] * temperature[:, None]
                exposure = (durations * prefactor / 4.0)[:, None]
                release_hazard += exposure * np.exp(np.minimum(40.0, -release_energy / thermal_energy))
                retention_hazard += exposure * np.exp(np.minimum(40.0, -retention_energy / thermal_energy))
            yields.append(-np.expm1(-release_hazard) * np.exp(-retention_hazard))
        weakest = np.minimum(yields[0].min(axis=1), yields[1].min(axis=1))
        means = np.minimum(yields[0].mean(axis=1), yields[1].mean(axis=1))
        return {"weakest": weakest, "mean": means, "history_gap": np.abs(yields[0].min(axis=1) - yields[1].min(axis=1))}

    def evaluate(self, orientation, controls, scenarios):
        native = self.native_state(orientation, controls)
        nominal = self.scenarios(native, [{"family": -1, "coordinates": [0.0] * 4}])
        response = self.scenarios(native, scenarios)
        family_yields = [min(value for value, scenario in zip(response["weakest"], scenarios) if scenario["family"] == family)
                         for family in range(4)]
        return {"nominal_mean": float(nominal["mean"][0]), "nominal_weakest": float(nominal["weakest"][0]),
                "joint_weakest": float(min(family_yields)), "family_yields": [float(value) for value in family_yields],
                "compatibility_fraction": float(np.mean(native["faults"][self.channels == -2])),
                "packing_fraction": float(np.mean(native["faults"][self.channels < 0])),
                "process_rms": float(np.sqrt(np.mean(native["residual"] ** 2))),
                "defects": int(np.sum(native["faults"])), "responses": {key: value.tolist() for key, value in response.items()}}
