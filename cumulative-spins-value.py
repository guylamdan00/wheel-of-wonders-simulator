#@title Cumulative Spins Value by Percentiles per Cumulative Spins Chart


# Prepare data for plotting - melt the percentile columns
cumulative_spins_value_melted = cumulative_spins_value_percentiles_table.melt(
    id_vars='cumulative_spins',
    value_vars=['mean', 'median', '25th_percentile', '75th_percentile', '90th_percentile', '95th_percentile'],
    var_name='statistic',
    value_name='cumulative_spins_value'
)

# Define the desired order of statistics for filtering
statistic_order = ['mean', 'median', '25th_percentile', '75th_percentile', '90th_percentile', '95th_percentile']

# Create a dropdown widget for selecting the statistic
statistic_filter = widgets.Dropdown(
    options=statistic_order,
    description='Select Statistic:',
    disabled=False,
)

# Define a function to update the plot based on the selected statistic
def update_cumulative_spins_value_plot(statistic):
    # Filter data for the selected statistic
    filtered_data = cumulative_spins_value_melted[cumulative_spins_value_melted['statistic'] == statistic].copy()

    plt.figure(figsize=(12, 7))
    ax = sns.barplot(data=filtered_data, x='cumulative_spins', y='cumulative_spins_value', palette='viridis')

    plt.title(f'Cumulative Spins Value by Cumulative Spins ({statistic})')
    plt.xlabel('Cumulative Spins')
    plt.ylabel('Cumulative Spins Value')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(rotation=0)

    # Add value labels on top of the bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f', label_type='edge', padding=3)

    plt.tight_layout()
    plt.show()

# Use interact to link the widget to the update function
interact(update_cumulative_spins_value_plot, statistic=statistic_filter);
