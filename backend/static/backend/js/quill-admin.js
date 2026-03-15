document.addEventListener('DOMContentLoaded', function () {
    var textareas = document.querySelectorAll('textarea[data-quill-editor="true"]');

    textareas.forEach(function (textarea) {
        if (textarea.dataset.quillReady === 'true') {
            return;
        }

        textarea.dataset.quillReady = 'true';
        textarea.style.display = 'none';

        var wrapper = document.createElement('div');
        wrapper.className = 'quill-admin-wrapper';

        var editor = document.createElement('div');
        editor.className = 'quill-admin-editor';
        editor.innerHTML = textarea.value || '';

        textarea.parentNode.insertBefore(wrapper, textarea);
        wrapper.appendChild(editor);
        wrapper.appendChild(textarea);

        var quill = new Quill(editor, {
            theme: 'snow',
            modules: {
                toolbar: [
                    [{ header: [1, 2, 3, false] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    [{ color: [] }, { background: [] }],
                    [{ list: 'ordered' }, { list: 'bullet' }],
                    [{ align: [] }],
                    ['link', 'blockquote'],
                    ['clean']
                ]
            }
        });

        quill.on('text-change', function () {
            textarea.value = quill.root.innerHTML;
        });

        var form = textarea.closest('form');
        if (form) {
            form.addEventListener('submit', function () {
                textarea.value = quill.root.innerHTML;
            });
        }
    });
});
