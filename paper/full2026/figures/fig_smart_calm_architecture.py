import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.path import Path
from matplotlib.patches import FancyArrowPatch


mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "font.size": 7,
    "axes.linewidth": 0.8,
    "legend.frameon": False,
})


INK = "#243040"
MUTED = "#67758A"
PANEL = "#F7F9FC"
LINE = "#3E4C5E"
DATA = "#25855A"
DATA_SOFT = "#E6F3ED"
FALLBACK = "#C74B52"
FALLBACK_SOFT = "#F9E6E6"
ACK = "#236EAE"
ACK_SOFT = "#E6F0FA"
STATE = "#8276B5"
STATE_SOFT = "#EFEAF8"
POLICY = "#D4922F"
POLICY_SOFT = "#FFF1D7"


def rounded_box(ax, xy, w, h, text="", fc="white", ec=LINE, lw=0.9,
                radius=0.06, fontsize=7, weight="normal", color=INK,
                ha="center", va="center"):
    box = patches.FancyBboxPatch(
        xy, w, h,
        boxstyle=patches.BoxStyle("Round", pad=0.015, rounding_size=radius),
        linewidth=lw, edgecolor=ec, facecolor=fc
    )
    ax.add_patch(box)
    if text:
        ax.text(xy[0] + w / 2, xy[1] + h / 2, text,
                ha=ha, va=va, fontsize=fontsize, color=color, weight=weight)
    return box


def circle_node(ax, xy, label, fc="white"):
    node = patches.Circle(xy, 0.19, edgecolor=INK, facecolor=fc, linewidth=1.05)
    ax.add_patch(node)
    ax.text(xy[0], xy[1], label, ha="center", va="center",
            fontsize=7.5, weight="bold", color=INK)
    return node


def arrow(ax, start, end, color=INK, lw=1.2, style="-", rad=0.0,
          mutation_scale=11, alpha=1.0):
    patch = FancyArrowPatch(
        start, end,
        arrowstyle="-|>",
        mutation_scale=mutation_scale,
        linewidth=lw,
        linestyle=style,
        color=color,
        alpha=alpha,
        shrinkA=5,
        shrinkB=5,
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(patch)
    return patch


def feedback_curve(ax, points, color=ACK, lw=1.2):
    path = Path(points, [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
    patch = patches.FancyArrowPatch(
        path=path,
        arrowstyle="-|>",
        mutation_scale=10,
        linewidth=lw,
        color=color,
    )
    ax.add_patch(patch)
    return patch


def small_label(ax, x, y, text, color=MUTED, ha="left", fontsize=6.2, weight="normal"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fontsize, color=color, weight=weight)


def draw_panel_a(ax):
    ax.text(0.02, 0.96, "a", transform=ax.transAxes, ha="left", va="top",
            fontsize=8, weight="bold", color=INK)
    ax.text(0.08, 0.96, "ACK-aware forwarding plane", transform=ax.transAxes,
            ha="left", va="top", fontsize=8, weight="bold", color=INK)

    s = (0.82, 1.95)
    r1 = (1.82, 2.46)
    r2 = (1.82, 1.40)
    d = (2.86, 1.95)
    circle_node(ax, s, "S", ACK_SOFT)
    circle_node(ax, r1, "R", DATA_SOFT)
    circle_node(ax, r2, "R", DATA_SOFT)
    circle_node(ax, d, "D", POLICY_SOFT)

    arrow(ax, s, r1, DATA, lw=1.6)
    arrow(ax, r1, d, DATA, lw=1.6)
    arrow(ax, s, r2, FALLBACK, lw=1.35, style=(0, (4, 3)))
    arrow(ax, r2, d, FALLBACK, lw=1.35, style=(0, (4, 3)))
    feedback_curve(ax, [(2.78, 1.72), (2.25, 0.78), (1.22, 0.78), (0.90, 1.72)], ACK, lw=1.25)

    y0 = 0.62
    arrow(ax, (0.48, y0), (0.92, y0), DATA, lw=1.25)
    small_label(ax, 1.00, y0, "DATA")
    arrow(ax, (1.50, y0), (1.94, y0), FALLBACK, lw=1.15, style=(0, (4, 3)))
    small_label(ax, 2.02, y0, "fallback")
    arrow(ax, (2.78, y0), (2.34, y0), ACK, lw=1.15)
    small_label(ax, 2.90, y0, "ACK")

    ax.text(0.42, 0.18, "Unicast is counted as delivered only after the source receives ACK.",
            ha="left", va="center", fontsize=6.2, color=MUTED)


def draw_panel_b(ax):
    ax.text(0.02, 0.96, "b", transform=ax.transAxes, ha="left", va="top",
            fontsize=8, weight="bold", color=INK)
    ax.text(0.08, 0.96, "Node-local online decision", transform=ax.transAxes,
            ha="left", va="top", fontsize=8, weight="bold", color=INK)

    rounded_box(ax, (0.24, 2.14), 1.15, 0.42, "Recent\nsignals", ACK_SOFT, fontsize=6.8)
    rounded_box(ax, (1.72, 2.14), 1.15, 0.42, "6-state\nbucket", STATE_SOFT, fontsize=6.8)
    rounded_box(ax, (3.18, 2.14), 1.15, 0.42, "Tabular Q\npolicy", POLICY_SOFT, fontsize=6.8)
    rounded_box(ax, (4.66, 2.14), 1.18, 0.42, "Profile\nchoice", FALLBACK_SOFT, fontsize=6.8)
    arrow(ax, (1.39, 2.35), (1.72, 2.35), LINE, lw=1.0)
    arrow(ax, (2.87, 2.35), (3.18, 2.35), LINE, lw=1.0)
    arrow(ax, (4.33, 2.35), (4.66, 2.35), LINE, lw=1.0)

    rounded_box(ax, (0.34, 0.88), 1.20, 0.52, "ACK success\ncache miss\ncollision", "white", fontsize=6.2)
    rounded_box(ax, (2.04, 0.88), 1.20, 0.52, "fallback\nrepair\nconfidence", "white", fontsize=6.2)
    rounded_box(ax, (3.74, 0.83), 1.65, 0.64,
                "reward = delivery\n- airtime - repairs\n- fallback pressure",
                "white", fontsize=6.0)

    arrow(ax, (0.92, 1.43), (0.82, 2.12), ACK, lw=0.9, alpha=0.85)
    arrow(ax, (2.58, 1.43), (2.30, 2.12), ACK, lw=0.9, alpha=0.85)
    arrow(ax, (4.50, 1.50), (3.76, 2.12), POLICY, lw=0.9, alpha=0.9)

    ax.text(3.06, 0.36, "Q <- Q + alpha [r + gamma max Q' - Q]",
            ha="center", va="center", fontsize=6.5, color=INK)


def draw_panel_c(ax):
    ax.text(0.015, 0.86, "c", transform=ax.transAxes, ha="left", va="top",
            fontsize=8, weight="bold", color=INK)
    ax.text(0.055, 0.86, "Profile selector closes the loop", transform=ax.transAxes,
            ha="left", va="top", fontsize=8, weight="bold", color=INK)

    xs = [0.58, 1.86, 3.10, 4.28, 5.42]
    labels = ["Data\nplane", "Outcome\nsignals", "State\nbucket", "Q-policy", "Lean\nBalanced\nRescue"]
    colors = [DATA_SOFT, ACK_SOFT, STATE_SOFT, POLICY_SOFT, FALLBACK_SOFT]
    widths = [0.88, 0.96, 0.96, 0.86, 0.96]
    for x, label, color, w in zip(xs, labels, colors, widths):
        rounded_box(ax, (x - w / 2, 1.32), w, 0.54, label, color, fontsize=6.4)
    for i in range(len(xs) - 1):
        arrow(ax, (xs[i] + widths[i] / 2, 1.59), (xs[i + 1] - widths[i + 1] / 2, 1.59),
              LINE, lw=1.0)

    feedback_curve(ax, [(5.42, 1.18), (4.78, 0.72), (1.12, 0.72), (0.58, 1.18)], LINE, lw=0.95)
    ax.text(3.12, 0.52, "profile choice rewrites route lifetime, discovery window and fallback scope",
            ha="center", va="center", fontsize=6.0, color=MUTED)

    ax.text(0.08, 0.22,
            "Controller state is local and small: no global topology service or neural policy is required.",
            ha="left", va="center", fontsize=6.1, color=MUTED)


def main():
    width_mm = 183
    height_mm = 104
    fig = plt.figure(figsize=(width_mm / 25.4, height_mm / 25.4), facecolor="white")

    ax_a = fig.add_axes([0.035, 0.39, 0.40, 0.53])
    ax_b = fig.add_axes([0.475, 0.39, 0.49, 0.53])
    ax_c = fig.add_axes([0.035, 0.075, 0.93, 0.255])

    for ax in (ax_a, ax_b, ax_c):
        ax.set_axis_off()
        ax.set_xlim(0, 6.2)
        ax.set_ylim(0, 3.0)
        rounded_box(ax, (0.02, 0.05), 6.12, 2.82, "", PANEL, ec="#D8DEE8", lw=0.65, radius=0.08)

    draw_panel_a(ax_a)
    draw_panel_b(ax_b)
    draw_panel_c(ax_c)

    fig.text(0.035, 0.965, "Smart-CALM: ACK-aware online redundancy control",
             ha="left", va="top", fontsize=8.5, weight="bold", color=INK)
    fig.text(0.035, 0.935,
             "A simple LoRa mesh data plane feeds a compact state-action controller that chooses per-flow redundancy profiles.",
             ha="left", va="top", fontsize=6.8, color=MUTED)

    base = "paper/full2026/figures/fig_smart_calm_architecture"
    fig.savefig(base + ".svg", bbox_inches="tight")
    fig.savefig(base + ".pdf", bbox_inches="tight")
    fig.savefig(base + ".tiff", dpi=600, bbox_inches="tight")
    fig.savefig(base + ".png", dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
