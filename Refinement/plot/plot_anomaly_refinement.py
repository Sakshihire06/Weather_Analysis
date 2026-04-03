import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REFINEMENT_DIR = os.path.dirname(CURRENT_DIR)
RESULTS_DIR = os.path.join(REFINEMENT_DIR, "results")
FIGURES_DIR = os.path.join(CURRENT_DIR, "figures")

CITY_ORDER = ["Mumbai", "Delhi", "Dehradun", "Jodhpur"]
CITY_COLORS = {
    "Mumbai": "#2196F3",
    "Delhi": "#F44336",
    "Dehradun": "#4CAF50",
    "Jodhpur": "#FF9800",
}

ANOMALY_PLOT_FILES = {
    "score_curve": os.path.join(FIGURES_DIR, "anomaly_threshold_scores.png"),
    "tradeoff_scatter": os.path.join(FIGURES_DIR, "anomaly_threshold_tradeoff.png"),
    "removed_values": os.path.join(FIGURES_DIR, "anomaly_values_removed.png"),
    "residual_heatmap": os.path.join(FIGURES_DIR, "anomaly_residual_outliers_heatmap.png"),
}


def ensure_plot_dir():
    os.makedirs(FIGURES_DIR, exist_ok=True)


def load_result(filename):
    path = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Result file not found: {path}")
    return pd.read_csv(path)


def save_figure(filename):
    ensure_plot_dir()
    output_path = os.path.join(FIGURES_DIR, filename)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    return output_path


def set_plot_style():
    sns.set_theme(style="whitegrid")


def plot_threshold_scores(all_df, show_plot=True):
    plt.figure(figsize=(10, 6))
    sns.lineplot(
        data=all_df,
        x="Threshold",
        y="Composite Score",
        hue="City",
        hue_order=CITY_ORDER,
        palette=CITY_COLORS,
        marker="o",
        linewidth=2,
    )
    plt.title("Anomaly Threshold Refinement: Composite Score by Threshold")
    plt.xlabel("Threshold")
    plt.ylabel("Composite Score")
    output_path = save_figure("anomaly_threshold_scores.png")
    if show_plot:
        plt.show()
    plt.close()
    print(f"Saved {output_path}")
    return output_path


def plot_threshold_tradeoff(all_df, show_plot=True):
    g = sns.relplot(
        data=all_df,
        x="Extra Missing After Threshold (%)",
        y="Residual Outliers (%)",
        col="City",
        col_order=CITY_ORDER,
        hue="Threshold",
        size="Known Extreme Preservation (%)",
        kind="scatter",
        height=4,
        aspect=1.0,
    )
    g.fig.suptitle("Anomaly Threshold Trade-off: Missingness vs Residual Outliers", y=1.05)
    for ax in g.axes.flat:
        ax.set_xlabel("Extra Missing After Threshold (%)")
        ax.set_ylabel("Residual Outliers (%)")
    output_path = save_figure("anomaly_threshold_tradeoff.png")
    if show_plot:
        plt.show()
    plt.close()
    print(f"Saved {output_path}")
    return output_path


def plot_removed_values(all_df, show_plot=True):
    plt.figure(figsize=(10, 6))
    sns.barplot(
        data=all_df,
        x="City",
        y="Anomaly Values Removed",
        hue="Threshold",
        order=CITY_ORDER,
        palette="crest",
    )
    plt.title("Anomaly Threshold Refinement: Values Removed Across Thresholds")
    plt.xlabel("City")
    plt.ylabel("Anomaly Values Removed")
    plt.legend(title="Threshold")
    output_path = save_figure("anomaly_values_removed.png")
    if show_plot:
        plt.show()
    plt.close()
    print(f"Saved {output_path}")
    return output_path


def plot_residual_heatmap(all_df, show_plot=True):
    heatmap_df = all_df.pivot(index="City", columns="Threshold", values="Residual Outliers (%)")
    heatmap_df = heatmap_df.reindex(CITY_ORDER)

    plt.figure(figsize=(9, 5))
    sns.heatmap(heatmap_df, annot=True, fmt=".2f", cmap="YlOrRd", linewidths=0.5)
    plt.title("Residual Outliers After Cleaning")
    plt.xlabel("Threshold")
    plt.ylabel("City")
    output_path = save_figure("anomaly_residual_outliers_heatmap.png")
    if show_plot:
        plt.show()
    plt.close()
    print(f"Saved {output_path}")
    return output_path


def generate_anomaly_refinement_plots(show_plots=True):
    set_plot_style()
    all_df = load_result("anomaly_threshold_refinement_all_results.csv")

    generated = {
        "score_curve": plot_threshold_scores(all_df, show_plot=show_plots),
        "tradeoff_scatter": plot_threshold_tradeoff(all_df, show_plot=show_plots),
        "removed_values": plot_removed_values(all_df, show_plot=show_plots),
        "residual_heatmap": plot_residual_heatmap(all_df, show_plot=show_plots),
    }
    return generated


def get_anomaly_plot_paths():
    return dict(ANOMALY_PLOT_FILES)


def ensure_anomaly_plots():
    missing_paths = [path for path in ANOMALY_PLOT_FILES.values() if not os.path.exists(path)]
    if missing_paths:
        return generate_anomaly_refinement_plots(show_plots=False)
    return get_anomaly_plot_paths()


def main():
    generate_anomaly_refinement_plots(show_plots=True)


if __name__ == "__main__":
    main()
