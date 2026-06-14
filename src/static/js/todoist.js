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
     * Render a single project with its tasks.
     *
     * Diff-based: unchanged tasks are updated in place (no animation),
     * new tasks slide in (.todo-enter), removed tasks animate out
     * (.todo-exit) and are dropped from the DOM afterwards.
     *
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

        headerEl.textContent = project.name || `Project ${index}`;
        const tasks = project.tasks || [];
        countEl.textContent = tasks.length;

        if (tasks.length === 0) {
            listEl.innerHTML = '<div class="todo-empty">No tasks</div>';
            return;
        }

        // Drop placeholders ("Loading...", "No tasks") and elements mid-exit
        for (const child of [...listEl.children]) {
            if (!child.classList.contains('todo-item') || child.classList.contains('todo-exit')) {
                child.remove();
            }
        }

        // Map current DOM elements by task id
        const existing = new Map();
        for (const child of listEl.children) {
            existing.set(child.dataset.taskId, child);
        }

        const newIds = tasks.map(t => String(t.id));
        const oldIds = [...existing.keys()];

        const updateInPlace = (elm, task) => {
            elm.className = `todo-item priority-${task.priority}`;
            const content = elm.querySelector('.todo-content');
            if (content) content.textContent = task.content;
        };

        // Common case: identical list (or only content edits) — refresh silently
        if (newIds.length === oldIds.length && newIds.every((id, i) => id === oldIds[i])) {
            tasks.forEach(t => updateInPlace(existing.get(String(t.id)), t));
            return;
        }

        // If surviving tasks were reordered, rebuild silently — animating a
        // reorder correctly isn't worth the complexity on a wall display
        const newIdSet = new Set(newIds);
        const survivingOld = oldIds.filter(id => newIdSet.has(id));
        const survivingNew = newIds.filter(id => existing.has(id));
        if (survivingOld.join() !== survivingNew.join()) {
            listEl.innerHTML = '';
            tasks.forEach(t => listEl.appendChild(this.createTaskElement(t)));
            return;
        }

        // Removed tasks: animate out where they stand, then remove
        existing.forEach((elm, id) => {
            if (!newIdSet.has(id)) {
                elm.classList.add('todo-exit');
                elm.addEventListener('animationend', () => elm.remove(), { once: true });
                existing.delete(id);
            }
        });

        // Added tasks: insert at their position with an enter animation.
        // Walk backwards so each insertion point (the next surviving task's
        // element) already exists.
        let nextEl = null;
        for (let i = tasks.length - 1; i >= 0; i--) {
            const task = tasks[i];
            let elm = existing.get(String(task.id));
            if (elm) {
                updateInPlace(elm, task);
            } else {
                elm = this.createTaskElement(task);
                elm.classList.add('todo-enter');
                listEl.insertBefore(elm, nextEl);
            }
            nextEl = elm;
        }
    },

    /**
     * Create a DOM element for a task
     * @param {Object} task - Task data
     * @returns {HTMLElement} Task element
     */
    createTaskElement(task) {
        const taskDiv = document.createElement('div');
        taskDiv.className = `todo-item priority-${task.priority}`;
        taskDiv.dataset.taskId = String(task.id);

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

