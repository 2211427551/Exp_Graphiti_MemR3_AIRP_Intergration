"""Generate performance comparison charts."""

import matplotlib.pyplot as plt
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False


def create_hash_performance_chart():
    """Create hash algorithm performance comparison chart."""
    algorithms = ['MD5', 'SHA256']
    performance = [377763, 554645]
    targets = [100000, 50000]

    x = np.arange(len(algorithms))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, performance, width, label='Actual', color='#2ecc71', alpha=0.8)
    bars2 = ax.bar(x + width/2, targets, width, label='Target', color='#e74c3c', alpha=0.8)

    ax.set_ylabel('Hashes per Second', fontsize=12, fontweight='bold')
    ax.set_title('Hash Algorithm Performance Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(algorithms)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:,.0f}',
                   ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    plt.savefig('hash_performance.png', dpi=300, bbox_inches='tight')
    print("✅ Generated: hash_performance.png")
    plt.close()


def create_change_detection_chart():
    """Create change detection performance chart."""
    scales = [100, 500, 1000, 5000]
    throughput = [234057, 334901, 497840, 523450]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(range(len(scales)), throughput, color='#3498db', alpha=0.8)

    ax.set_xlabel('Number of Entries', fontsize=12, fontweight='bold')
    ax.set_ylabel('Throughput (entries/second)', fontsize=12, fontweight='bold')
    ax.set_title('Change Detection Performance vs Scale', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(scales)))
    ax.set_xticklabels([f'{s:,}' for s in scales])
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:,.0f}',
               ha='center', va='bottom', fontsize=10)

    # Add target line
    ax.axhline(y=1000, color='#e74c3c', linestyle='--', linewidth=2, label='Target (1K/s)')
    ax.legend()

    plt.tight_layout()
    plt.savefig('change_detection_performance.png', dpi=300, bbox_inches='tight')
    print("✅ Generated: change_detection_performance.png")
    plt.close()


def create_latency_chart():
    """Create latency comparison chart."""
    scales = [100, 500, 1000, 5000]
    latency = [0.43, 1.49, 2.01, 9.55]
    target_latency = [1000, 1000, 1000, 1000]  # 1 second target

    x = np.arange(len(scales))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, latency, width, label='Actual (ms)', color='#2ecc71', alpha=0.8)
    bars2 = ax.bar(x + width/2, target_latency, width, label='Target (ms)', color='#e74c3c', alpha=0.8)

    ax.set_ylabel('Detection Time (ms)', fontsize=12, fontweight='bold')
    ax.set_title('Change Detection Latency Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{s:,}' for s in scales])
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    ax.set_yscale('log')

    # Add value labels
    for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
        height1 = bar1.get_height()
        height2 = bar2.get_height()
        ax.text(bar1.get_x() + bar1.get_width()/2., height1,
               f'{height1:.2f}ms',
               ha='center', va='bottom', fontsize=9)
        ax.text(bar2.get_x() + bar2.get_width()/2., height2,
               f'{height2:.0f}ms',
               ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig('latency_comparison.png', dpi=300, bbox_inches='tight')
    print("✅ Generated: latency_comparison.png")
    plt.close()


def create_summary_radar_chart():
    """Create summary radar chart."""
    categories = ['Hash Speed', 'Detection Speed', 'Memory Efficiency', 'Accuracy', 'Cache Hit Rate']

    # Normalized scores (0-100)
    actual_scores = [90, 95, 85, 100, 100]
    target_scores = [50, 60, 70, 100, 80]

    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    actual_scores += actual_scores[:1]
    target_scores += target_scores[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

    ax.plot(angles, actual_scores, 'o-', linewidth=2, label='Actual', color='#2ecc71')
    ax.fill(angles, actual_scores, alpha=0.25, color='#2ecc71')
    ax.plot(angles, target_scores, 'o-', linewidth=2, label='Target', color='#e74c3c')
    ax.fill(angles, target_scores, alpha=0.25, color='#e74c3c')

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=9)
    ax.grid(True)

    plt.title('Performance Summary - Actual vs Target', fontsize=14, fontweight='bold', pad=20)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

    plt.tight_layout()
    plt.savefig('performance_summary_radar.png', dpi=300, bbox_inches='tight')
    print("✅ Generated: performance_summary_radar.png")
    plt.close()


def create_throughput_comparison():
    """Create throughput comparison across different scenarios."""
    scenarios = ['100 entries', '500 entries', '1000 entries', '5000 entries']
    throughput = [234057, 334901, 497840, 523450]

    fig, ax = plt.subplots(figsize=(12, 6))
    line = ax.plot(range(len(scenarios)), throughput, marker='o', linewidth=3,
                   markersize=10, color='#3498db', label='Throughput')

    ax.set_xlabel('Dataset Size', fontsize=12, fontweight='bold')
    ax.set_ylabel('Throughput (entries/second)', fontsize=12, fontweight='bold')
    ax.set_title('Scalability Analysis', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels(scenarios, rotation=15, ha='right')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Add value labels
    for i, v in enumerate(throughput):
        ax.text(i, v + 10000, f'{v:,.0f}',
               ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Add target line
    ax.axhline(y=1000, color='#e74c3c', linestyle='--', linewidth=2, label='Target (1K/s)')

    plt.tight_layout()
    plt.savefig('scalability_analysis.png', dpi=300, bbox_inches='tight')
    print("✅ Generated: scalability_analysis.png")
    plt.close()


def main():
    """Generate all performance charts."""
    print("\n" + "="*70)
    print("  Generating Performance Visualization Charts")
    print("="*70 + "\n")

    create_hash_performance_chart()
    create_change_detection_chart()
    create_latency_chart()
    create_summary_radar_chart()
    create_throughput_comparison()

    print("\n" + "="*70)
    print("  All charts generated successfully!")
    print("="*70)
    print("\nGenerated files:")
    print("  📊 hash_performance.png")
    print("  📊 change_detection_performance.png")
    print("  📊 latency_comparison.png")
    print("  📊 performance_summary_radar.png")
    print("  📊 scalability_analysis.png")
    print()


if __name__ == "__main__":
    main()
