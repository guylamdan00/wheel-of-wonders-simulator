#@title Distribution of Players by Spins to Complete Level

# Calculate the distribution of spins to complete a level for each level
spins_distribution = spins_to_levelup.groupby('level')['spins_to_complete_level'].value_counts(normalize=True).mul(100).reset_index(name='percentage')

# Get unique levels for the level filter, including an "All" option
level_options_dist = sorted(spins_distribution['level'].unique().tolist())
level_options_dist.insert(0, 'All')

# Create a dropdown widget for selecting the level
level_filter_dist = widgets.Dropdown(
    options=level_options_dist,
    description='Select Level:',
    disabled=False,
)

# Define a function to update the plot based on the selected level
def update_spins_distribution_plot(level):
    # Filter data for the selected level
    if level == 'All':
        filtered_data = spins_distribution.copy()
        title_level = 'All Levels'
    else:
        filtered_data = spins_distribution[spins_distribution['level'] == level].copy()
        title_level = f'Level {level}'

    plt.figure(figsize=(12, 7))
    ax = sns.barplot(data=filtered_data, x='spins_to_complete_level', y='percentage', hue='level' if level == 'All' else None, palette='viridis')

    plt.title(f'Distribution of Players (%) by Spins to Complete Level ({title_level})')
    plt.xlabel('Spins to Complete Level')
    plt.ylabel('Percentage of Players (%)')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(rotation=0)

    # Add value labels on top of the bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f%%', label_type='edge', padding=3) # Added %% for the percentage sign

    plt.tight_layout()
    plt.show()

# Use interact to link the widget to the update function
interact(update_spins_distribution_plot, level=level_filter_dist);
