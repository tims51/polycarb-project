# Adjust Sidebar Backup Display Plan

I will update the sidebar to optimize the display of the latest backup information and ensure a responsive, collapsible design for mobile and internet access.

## 1. Backup Status Display (app/components/sidebar.py)
- **Collapsible Design**: Wrap the backup status in an `st.expander` with the title "💾 备份状态" (Backup Status) to keep the default view simplified.
- **Font Optimization**: Set the font size of the timestamp to `0.85em` (approx. 15% smaller than standard) to ensure the full date and time (`YYYY-MM-DD HH:MM:SS`) fits clearly within the sidebar.
- **Content**: Ensure only the project and experiment metrics are shown (Raw Materials count already removed).

## 2. Access Information (app/components/access_manager.py)
- **Verification**: Confirm that "Mobile Access" and "Internet Access" sections are using `st.expander` to support the collapsible/expandable interaction required for mobile adaptation. (Note: These were updated in the previous step, will ensure consistency).

## 3. User Interface
- **Interaction**: Users will click "💾 备份状态" to reveal the detailed backup timestamp.
- **Responsiveness**: The collapsible design ensures the sidebar remains uncluttered on smaller mobile screens.
