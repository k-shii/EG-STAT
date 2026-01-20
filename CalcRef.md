# EG‑Stat — Physics & Math Reference (v0.1.0)

This document lists the core physics and equations used by EG‑Stat.

Goal: transparency. You can reproduce outputs by applying these equations to the same inputs and assumptions.
---

## Conventions and units

* **RPM** in revolutions per minute.
* **Angular speed** $\omega$ in rad/s.
* **Torque** $T$ in N·m.
* **Power** $P$ in W or kW.
* **Displacement** $V_d$ in m³ (litres shown as L).
* **BMEP** in Pa (internally) or kPa (UI/output).
* **Speed** $v$ in m/s (sometimes reported as km/h).
* **Air density** $\rho$ in kg/m³.
* **Cd** (drag coefficient) is dimensionless.
* **Frontal area** $A$ in m².
* **Rolling resistance coefficient** $C_{rr}$ is dimensionless.
* **Gravity** $g = 9.80665,\text{m/s}^2$.

---

## 1) RPM ↔ angular speed

$$
\omega = \frac{2\pi,\text{RPM}}{60}
$$

Used for converting engine speed to rad/s.

---

## 2) Engine displacement

### 2.1 Bore/stroke/cylinders → displacement

For a multi‑cylinder engine:

$$
V_d = \left(\frac{\pi}{4}\right),B^2,S,N
$$

Where:

* $B$ = bore (m)
* $S$ = stroke (m)
* $N$ = number of cylinders

### 2.2 Displacement display

$$
V_{d,\text{L}} = 1000,V_d
$$

since $1,\text{m}^3 = 1000,\text{L}$.

---

## 3) Mean piston speed

$$
\bar{u}_p = 2S\left(\frac{\text{RPM}}{60}\right)
$$

Where $S$ is stroke in meters.

---

## 4) BMEP ↔ torque relationship

EG‑Stat uses the standard cycle‑work identity:

$$
W_\text{cycle} = \text{BMEP}\cdot V_d = T\cdot \theta_\text{cycle}
$$

Where $\theta_\text{cycle}$ is the crank angle (radians) per **power cycle**.

### 4.1 Crank angle per power cycle

* **4‑stroke:** one power event per cylinder every **2** revolutions
  $$
  \theta_\text{cycle} = 4\pi
  $$

* **2‑stroke:** one power event per cylinder every **1** revolution
  $$
  \theta_\text{cycle} = 2\pi
  $$

(Internally this is implemented with `revs_per_power` = 2 or 1.)

### 4.2 Torque from BMEP

$$
T = \frac{\text{BMEP}\cdot V_d}{2\pi,r}
$$

Where:

* $r$ = revolutions per power cycle (2 for 4‑stroke, 1 for 2‑stroke)

### 4.3 BMEP from torque

$$
\text{BMEP} = \frac{T,(2\pi,r)}{V_d}
$$

### 4.4 Unit conversion

$$
\text{BMEP}*{\text{Pa}} = 1000,\text{BMEP}*{\text{kPa}}
$$

---

## 5) Power from torque and RPM

### 5.1 Power in watts

$$
P = T,\omega
$$

### 5.2 Power in kilowatts

$$
P_{\text{kW}} = \frac{P}{1000}
$$

### 5.3 Torque from power and RPM

$$
T = \frac{P}{\omega}
$$

---

## 6) Template curve system (normalized load vs RPM)

EG‑Stat uses a **template profile** that returns a normalized factor $f(x)\in[0,1]$ as a function of RPM fraction.

### 6.1 RPM fraction

$$
x = \mathrm{clamp}\left(\frac{\text{RPM} - \text{RPM}*{\text{idle}}}{\text{RPM}*{\text{redline}} - \text{RPM}_{\text{idle}}},;0,;1\right)
$$

### 6.2 Profile factor (piecewise linear)

A profile defines points $(x_i, y_i)$. For $x\in[x_i, x_{i+1}]$:

$$
f(x) = y_i + \left(\frac{x-x_i}{x_{i+1}-x_i}\right)(y_{i+1}-y_i)
$$

Outside range, values are clamped to the endpoints.

### 6.3 BMEP curve from profile

Given a user‑supplied peak BMEP and a profile factor:

$$
\text{BMEP}(\text{RPM}) = \text{BMEP}_{\text{peak}}\cdot f(x)
$$

Then torque and power curves are computed from sections 4 and 5.

---

## 7) Fuel consumption (BSFC‑based)

EG‑Stat estimates fuel flow using BSFC (Brake Specific Fuel Consumption).

### 7.1 Mass fuel flow

$$
\dot{m}_{\text{fuel}},(\text{g/h}) = \text{BSFC},(\text{g/kWh})\cdot P,(\text{kW})
$$

Convert to kg/h:

$$
\dot{m}*{\text{fuel}},(\text{kg/h}) = \frac{\dot{m}*{\text{fuel}},(\text{g/h})}{1000}
$$

### 7.2 Volume fuel flow

$$
\dot{V}*{\text{fuel}},(\text{L/h}) = \frac{\dot{m}*{\text{fuel}},(\text{kg/h})}{\rho_{\text{fuel}},(\text{kg/L})}
$$

### 7.3 Default BSFC (estimate mode)

If the user does not supply BSFC, EG‑Stat uses a defensible default by fuel type:

* Diesel: ~230 g/kWh
* Petrol: ~270 g/kWh
* E85: ~320 g/kWh

### 7.4 Outputs reported

* **WOT at peak power**: fuel at $P = P_{\text{peak}}$
* **Cruise placeholder**: fuel at $P = 20,\text{kW}$ (intentionally simple baseline)

---

## 8) Drivetrain & vehicle speed

### 8.1 Wheel RPM from engine RPM

$$
\text{RPM}*{\text{wheel}} = \frac{\text{RPM}*{\text{engine}}}{G,F}
$$

Where:

* $G$ = gear ratio
* $F$ = final drive ratio

### 8.2 Speed from wheel RPM and tire radius

Wheel circumference:

$$
C = 2\pi R
$$

Vehicle speed:

$$
v = \frac{\text{RPM}_{\text{wheel}},C}{60}
$$

Convert to km/h:

$$
v_{\text{km/h}} = 3.6,v
$$

### 8.3 Per‑gear redline speed

Computed using $\text{RPM}*{\text{engine}} = \text{RPM}*{\text{redline}}$ in each gear.

---

## 9) Road load power (flat road)

EG‑Stat uses a basic longitudinal road load model:

$$
P_{\text{req}}(v) = P_{\text{aero}}(v) + P_{\text{rr}}(v)
$$

### 9.1 Aerodynamic power

$$
P_{\text{aero}} = \tfrac{1}{2},\rho,(C_d A),v^3
$$

### 9.2 Rolling resistance power

Rolling resistance force:

$$
F_{\text{rr}} = C_{rr},m,g
$$

Rolling power:

$$
P_{\text{rr}} = F_{\text{rr}},v
$$

Assumptions:

* No road grade (0% incline)
* No wind
* No drivetrain thermal limits

---

## 10) Top speed estimate

EG‑Stat estimates top speed by scanning candidate points across gears and RPM samples.

### 10.1 Available wheel power

$$
P_{\text{avail}}(\text{RPM}) = \eta,P_{\text{engine}}(\text{RPM})
$$

Where $\eta$ is drivetrain efficiency.

### 10.2 Feasibility condition

A speed point is feasible if:

$$
P_{\text{avail}} \ge P_{\text{req}}
$$

The maximum feasible speed across gears/RPM samples is returned as the estimated top speed.

---

## 11) Upshift recommendation (wheel‑torque crossover)

EG‑Stat recommends an upshift RPM when the next gear produces equal or greater wheel torque than the current gear.

For a shift from gear $G_1$ to $G_2$:

* RPM after shift is approximated by the ratio drop:

$$
\text{RPM}_2 = \text{RPM}_1\left(\frac{G_2}{G_1}\right)
$$

* Wheel torque comparison (final drive cancels):

$$
T_{w1} = T(\text{RPM}_1),G_1
$$

$$
T_{w2} = T(\text{RPM}_2),G_2
$$

Choose the earliest $\text{RPM}_1$ where:

$$
T_{w2} \ge T_{w1}
$$

If no crossover is found, shift at redline.

---

## Notes on scope

* EG‑Stat is **an estimator**, not a dyno model. Accuracy depends on how realistic the chosen BMEP, template profile, BSFC, and vehicle parameters are.
* The template profile system is intentionally simple and transparent. More advanced versions can add VE maps, boost models, thermal limits, and drivetrain loss maps while retaining these fundamentals.
