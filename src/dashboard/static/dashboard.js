// CanillitaBot Dashboard JavaScript - Simplified

// Global state
let refreshInterval;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadPosts();
    setupModal();
    refreshInterval = setInterval(loadPosts, 30000); // Refresh every 30 seconds
});

// Setup modal functionality
function setupModal() {
    const modal = document.getElementById('comment-modal');
    const closeBtn = document.querySelector('.close');
    
    closeBtn.onclick = function() {
        modal.style.display = 'none';
    };
    
    window.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };
}

// Show post comment in modal
function showComment(postId, title, comment) {
    const modal = document.getElementById('comment-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalComment = document.getElementById('modal-comment');
    
    modalTitle.textContent = title;
    modalComment.textContent = comment || 'No se generó comentario para este post.';
    modal.style.display = 'block';
}

// Retry post processing
function retryPost(postId, button) {
    button.disabled = true;
    button.textContent = 'Procesando...';
    
    fetch(`/api/retry-post/${postId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            button.textContent = 'Enviado';
            setTimeout(() => {
                loadPosts(); // Refresh the list
            }, 2000);
        } else {
            button.textContent = 'Error';
            button.style.background = '#e74c3c';
        }
    })
    .catch(error => {
        console.error('Error retrying post:', error);
        button.textContent = 'Error';
        button.style.background = '#e74c3c';
    })
    .finally(() => {
        setTimeout(() => {
            button.disabled = false;
            button.textContent = 'Reintentar';
            button.style.background = '#3498db';
        }, 3000);
    });
}

// Fetch new posts from subreddit
function fetchNewPosts() {
    const button = document.getElementById('fetch-posts-btn');
    const originalText = button.innerHTML;
    
    button.disabled = true;
    button.innerHTML = '⏳ Buscando posts...';
    
    fetch('/api/fetch-new-posts', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.found_posts > 0) {
                button.innerHTML = `✅ ${data.found_posts} posts nuevos encontrados`;
                // Show a brief summary of what was found
                console.log('New posts found:', data.posts);
                // Refresh the posts list after a short delay to show if any got processed
                setTimeout(() => {
                    loadPosts();
                }, 2000);
            } else {
                button.innerHTML = '✅ No hay posts nuevos';
            }
        } else {
            button.innerHTML = '❌ Error al buscar';
            console.error('Error fetching posts:', data.error);
        }
    })
    .catch(error => {
        console.error('Error fetching new posts:', error);
        button.innerHTML = '❌ Error de conexión';
    })
    .finally(() => {
        setTimeout(() => {
            button.disabled = false;
            button.innerHTML = originalText;
        }, 4000);
    });
}
function loadPosts() {
    fetch('/api/posts?limit=50')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('posts-container');
            if (data.length === 0) {
                container.innerHTML = '<p>No hay posts procesados</p>';
                return;
            }
            
            let html = `
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Título del Post</th>
                                <th>Resultado</th>
                                <th>Fecha</th>
                                <th>Acción</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            data.forEach(post => {
                const statusClass = post.success ? 'success' : 'error';
                const statusText = post.success ? '✅ Exitoso' : '❌ Error';
                const truncatedTitle = post.title.length > 80 ? 
                    post.title.substring(0, 80) + '...' : post.title;
                
                html += `
                    <tr>
                        <td>
                            <span class="post-title" 
                                  onclick="showComment('${post.post_id}', '${post.title.replace(/'/g, "\\'")}', '${(post.comment_text || '').replace(/'/g, "\\'")}')">
                                ${truncatedTitle}
                            </span>
                        </td>
                        <td class="${statusClass}">${statusText}</td>
                        <td>${post.processed_at_readable || 'N/A'}</td>
                        <td>
                            <button class="retry-btn" 
                                    onclick="retryPost('${post.post_id}', this)">
                                Reintentar
                            </button>
                        </td>
                    </tr>
                `;
            });
            
            html += '</tbody></table></div>';
            container.innerHTML = html;
            
            // Update last refresh time
            document.getElementById('last-update').textContent = 
                new Date().toLocaleTimeString('es-AR');
        })
        .catch(error => {
            console.error('Error loading posts:', error);
            document.getElementById('posts-container').innerHTML = 
                '<p class="error">Error cargando posts</p>';
        });
}
