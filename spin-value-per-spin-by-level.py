#@title Spins Value per Spin by Level

# Prepare data for plotting - melt the percentile columns
spins_value_melted = percentile_spins_value_per_spin.melt(
    id_vars=['level', 'spin'],
    value_vars=['mean', 'median', '75th_percentile', '90th_percentile', '95th_percentile'],
    var_name='statistic',
    value_name='spins_value'
)

# Define the desired order of statistics for filtering
statistic_order = ['mean', 'median', '75th_percentile', '90th_percentile', '95th_percentile']

# Create a dropdown widget for selecting the statistic
statistic_filter = widgets.Dropdown(
    options=statistic_order,
    description='Select Statistic:',
    disabled=False,
)

# Get unique levels for the level filter, including an "All" option
level_options = sorted(spins_value_melted['level'].unique().tolist())
level_options.insert(0, 'All')

# Create a dropdown widget for selecting the level
level_filter = widgets.Dropdown(
    options=level_options,
    description='Select Level:',
    disabled=False,
)


# Define a function to update the plot based on the selected statistic and level
def update_spins_value_plot(statistic, level):
    # Filter data for the selected statistic
    filtered_data = spins_value_melted[spins_value_melted['statistic'] == statistic].copy()

    # Apply level filter if "All" is not selected
    if level != 'All':
        filtered_data = filtered_data[filtered_data['level'] == level]

    # Create a pivot table to get levels as columns and spins as index
    pivot_data = filtered_data.pivot(index='spin', columns='level', values='spins_value')

    plt.figure(figsize=(14, 8)) # Increased figure size
    ax = pivot_data.plot(kind='bar', colormap='viridis', ax=plt.gca(), width=0.8) # Increased bar width

    plt.title(f'Spins Value per Spin by Level ({statistic})' + (f' - Level {level}' if level != 'All' else ' - All Levels'))
    plt.xlabel('Spin Number')
    plt.ylabel('Spins Value')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(rotation=0)
    plt.legend(title='Level')

    # Add value labels on top of the bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f', label_type='edge', padding=3)


    plt.tight_layout()
    plt.show()

# Use interact to link the widgets to the update function
interact(update_spins_value_plot, statistic=statistic_filter, level=level_filter);
