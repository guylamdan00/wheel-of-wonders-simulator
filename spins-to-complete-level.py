#@title Spins to Complete by Level per Percentile

# 1. Spins to complete level by percentile/Min/Max
# Filter for levelup events
levelup_spins = score_data_filtered[score_data_filtered['wedge_type'] == 'levelup'].copy()

# Calculate spins to level up for each player at each level
spins_to_levelup = levelup_spins.groupby(['player_id', 'level'])['spin'].min().reset_index()
spins_to_levelup.rename(columns={'spin': 'spins_to_complete_level'}, inplace=True)

# Calculate min, max, mean, and percentiles of spins to complete level by level
spins_completion_stats = spins_to_levelup.groupby('level')['spins_to_complete_level'].agg(['min', 'max', 'mean', lambda x: x.quantile(0.25), lambda x: x.quantile(0.5), lambda x: x.quantile(0.75)]).reset_index()
spins_completion_stats.rename(columns={'<lambda_0>': '25th_percentile', '<lambda_1>': '50th_percentile', '<lambda_2>': '75th_percentile'}, inplace=True)

print("Spins to Complete Level by Percentile/Min/Max/Mean:")
# display(spins_completion_stats)

# Prepare data for plotting - melt the percentile columns
spins_completion_melted = spins_completion_stats.melt(
    id_vars='level',
    value_vars=['min', 'max', 'mean', '25th_percentile', '50th_percentile', '75th_percentile'],
    var_name='statistic',
    value_name='spins'
)

# Define the desired order of statistics for filtering
statistic_order = ['min', '25th_percentile', '50th_percentile', '75th_percentile', 'max', 'mean']

# Create a dropdown widget for selecting the statistic
statistic_filter = widgets.Dropdown(
    options=statistic_order,
    description='Select Statistic:',
    disabled=False,
)

# Define a function to update the plot based on the selected statistic
def update_plot(statistic):
    filtered_data = spins_completion_melted[spins_completion_melted['statistic'] == statistic]

    plt.figure(figsize=(10, 6))
    ax = sns.barplot(data=filtered_data, x='level', y='spins', palette='viridis')

    plt.title(f'Spins to Complete Level ({statistic})')
    plt.xlabel('Level')
    plt.ylabel('Number of Spins')
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Add value labels on top of the bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f', label_type='edge')

    plt.show()

# Use interact to link the widget to the update function
interact(update_plot, statistic=statistic_filter);
