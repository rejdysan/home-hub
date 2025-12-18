/**
 * Todoist List Management
 * Handles rendering and updating of Todoist tasks
 */

const TodoistManager = {
    /**
     * Update Todoist display with new data
     * @param {Object} data - Todoist data containing projects array
     */
    update(data) {
        if (!data || !data.projects) {
            console.warn('Invalid Todoist data received');
            return;
        }

        // Update timestamp
        const updateEl = document.getElementById('update-todoist');
        if (updateEl) {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('en-GB', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            updateEl.textContent = `Updated: ${timeStr}`;
        }

        // Display each project
        data.projects.forEach((project, index) => {
            const listIndex = index + 1;
            this.renderProject(project, listIndex);
        });
    },

    /**
     * Render a single project with its tasks
     * @param {Object} project - Project data
     * @param {number} index - Project index (1 or 2)
     */
    renderProject(project, index) {
        const headerEl = document.getElementById(`todo-header-${index}`);
        const listEl = document.getElementById(`todo-list-${index}`);
        const countEl = document.getElementById(`todo-count-${index}`);

        if (!headerEl || !listEl || !countEl) {
            console.warn(`Todo elements not found for index ${index}`);
            return;
        }

        // Update header with project name
        headerEl.textContent = project.name || `Project ${index}`;

        // Update task count
        const taskCount = project.tasks ? project.tasks.length : 0;
        countEl.textContent = taskCount;

        // Clear existing tasks
        listEl.innerHTML = '';

        // Render tasks
        if (!project.tasks || project.tasks.length === 0) {
            listEl.innerHTML = '<div class="todo-empty">No tasks</div>';
            return;
        }

        project.tasks.forEach(task => {
            const taskEl = this.createTaskElement(task);
            listEl.appendChild(taskEl);
        });
    },

    /**
     * Create a DOM element for a task
     * @param {Object} task - Task data
     * @returns {HTMLElement} Task element
     */
    createTaskElement(task) {
        const taskDiv = document.createElement('div');
        taskDiv.className = `todo-item priority-${task.priority}`;

        // Create checkbox
        const checkbox = document.createElement('div');
        checkbox.className = 'todo-checkbox';

        // Create content
        const content = document.createElement('div');
        content.className = 'todo-content';
        content.textContent = task.content;

        taskDiv.appendChild(checkbox);
        taskDiv.appendChild(content);

        return taskDiv;
    },

    /**
     * Initialize Todoist display
     */
    init() {
        console.log('📝 Todoist manager initialized');
    }
};

// Initialize on load
TodoistManager.init();

