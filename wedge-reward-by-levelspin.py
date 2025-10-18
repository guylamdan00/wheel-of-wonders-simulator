#@title Wedge Reward Heatmap by Spin and Level (Player Distribution %)

# Get unique levels for the level filter, including an "All" option
level_options_heatmap = sorted(heatmap_data.columns.get_level_values('level').unique().tolist())
level_options_heatmap.insert(0, 'All')

# Create a dropdown widget for selecting the level
level_filter_heatmap = widgets.Dropdown(
    options=level_options_heatmap,
    description='Select Level:',
    disabled=False,
)


# Define a function to update the heatmap based on the selected level
def update_heatmap(level):
    plt.figure(figsize=(20, 10)) # Adjust figure size as needed

    # Filter data for the selected level
    if level == 'All':
        filtered_heatmap_data = heatmap_data.copy()
        title_level = 'All Levels'
    else:
        # Select columns for the chosen level. This handles the MultiIndex.
        # We need to select ALL columns where the first level of the MultiIndex is the selected level.
        filtered_heatmap_data = heatmap_data.loc[:, heatmap_data.columns.get_level_values('level') == level]
        title_level = f'Level {level}'

    # Add a small gap between levels if 'All' is selected
    if level == 'All':
        # Find unique levels in the filtered data
        unique_levels = filtered_heatmap_data.columns.get_level_values('level').unique()
        heatmap_data_with_gaps = pd.DataFrame()
        for lvl in unique_levels:
            level_cols = filtered_heatmap_data.loc[:, filtered_heatmap_data.columns.get_level_values('level') == lvl]
            heatmap_data_with_gaps = pd.concat([heatmap_data_with_gaps, level_cols], axis=1)
            # Add a gap column between levels (except after the last one)
            if lvl != unique_levels[-1]:
                gap_col = pd.DataFrame(np.nan, index=heatmap_data_with_gaps.index, columns=[('Gap', '', '', '')])
                heatmap_data_with_gaps = pd.concat([heatmap_data_with_gaps, gap_col], axis=1)

        plot_data = heatmap_data_with_gaps
    else:
        plot_data = filtered_heatmap_data


    ax = sns.heatmap(plot_data, cmap='viridis', annot=True, fmt=".1f", linewidths=.5, annot_kws={'fontsize': 10})

    plt.title(f'Distribution of Players (%) by Wedge Reward, Spin, and Level ({title_level})')
    plt.ylabel('Spin Number')
    plt.tight_layout()

    # Set up dual x-axes for Level and Wedge Reward + Amount
    # Bottom axis for Level
    ax.xaxis.set_ticks_position('bottom')
    ax.xaxis.set_label_position('bottom')
    plt.xlabel('Level and Wedge Number') # Updated label to reflect both

    # Top axis for Wedge Reward + Amount
    ax2 = ax.twiny()
    ax2.set_xlabel('Wedge Reward and Amount') # Updated label
    ax2.set_xlim(ax.get_xlim())

    # Adjust tick positions and labels for the top axis to match the flattened column structure,
    # accounting for potential 'Gap' columns if 'All' is selected.
    top_labels = []
    top_tick_positions = []
    current_pos = 0.5 # Start halfway into the first column

    for i, col in enumerate(plot_data.columns):
        if col[0] == 'Gap':
            # If it's a gap column, just move the position
            current_pos += 1
        else:
            # For regular data columns, add label and position
            top_labels.append(f'{col[2]} ({col[3]:.1f})')
            top_tick_positions.append(current_pos)
            current_pos += 1 # Move to the next position

    ax2.set_xticks(top_tick_positions)
    ax2.set_xticklabels(top_labels)

    ax2.xaxis.set_ticks_position('top')
    ax2.xaxis.set_label_position('top')
    plt.setp(ax2.get_xticklabels(), rotation=45, ha="left") # Rotate labels for better readability


    # Adjust bottom axis labels to show Level and Wedge Number
    bottom_labels = []
    bottom_tick_positions = []
    current_pos = 0.5

    for i, col in enumerate(plot_data.columns):
        if col[0] == 'Gap':
            bottom_labels.append('') # No label for gap
        else:
            bottom_labels.append(f'L{col[0]} W{col[1]}')

        bottom_tick_positions.append(current_pos)
        current_pos += 1

    ax.set_xticks(bottom_tick_positions)
    ax.set_xticklabels(bottom_labels, rotation=45, ha="right")


    # Manually add '%' sign to annotations
    for text in ax.texts:
        # Check if the text is a number before adding '%'
        try:
            float(text.get_text())
            text.set_text(text.get_text() + '%')
        except ValueError:
            pass # Don't add '%' to non-numeric annotations (like NaN from gaps)


    plt.show()

# Use interact to link the widget to the update function
interact(update_heatmap, level=level_filter_heatmap);
