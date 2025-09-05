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

// Show post comment or error details in modal
function showComment(postId, title, comment, errorMessage = null) {
    const modal = document.getElementById('comment-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalComment = document.getElementById('modal-comment');
    
    modalTitle.textContent = title;
    
    if (errorMessage) {
        // Show error information
        modalComment.innerHTML = `
            <div style="color: #e74c3c; background: #fdf2f2; padding: 10px; border-radius: 5px; border-left: 4px solid #e74c3c;">
                <strong>❌ Error de procesamiento:</strong><br>
                ${errorMessage}
            </div>
        `;
    } else {
        // Show comment as plain text (no markdown rendering)
        modalComment.textContent = comment || 'No se generó comentario para este post.';
    }
    
    modal.style.display = 'block';
}

// Show comment by fetching from API (safer approach)
function showCommentFromAPI(postId, title) {
    const modal = document.getElementById('comment-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalComment = document.getElementById('modal-comment');
    
    modalTitle.textContent = title;
    modalComment.textContent = 'Cargando comentario...';
    modal.style.display = 'block';
    
    fetch(`/api/posts/${postId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                modalComment.innerHTML = `
                    <div style="color: #e74c3c; background: #fdf2f2; padding: 10px; border-radius: 5px; border-left: 4px solid #e74c3c;">
                        <strong>❌ Error:</strong><br>
                        ${data.error}
                    </div>
                `;
            } else if (data.error_message) {
                modalComment.innerHTML = `
                    <div style="color: #e74c3c; background: #fdf2f2; padding: 10px; border-radius: 5px; border-left: 4px solid #e74c3c;">
                        <strong>❌ Error de procesamiento:</strong><br>
                        ${data.error_message}
                    </div>
                `;
            } else {
                modalComment.textContent = data.comment_content || 'No se generó comentario para este post.';
            }
        })
        .catch(error => {
            console.error('Error fetching comment:', error);
            modalComment.innerHTML = `
                <div style="color: #e74c3c; background: #fdf2f2; padding: 10px; border-radius: 5px; border-left: 4px solid #e74c3c;">
                    <strong>❌ Error de conexión:</strong><br>
                    No se pudo cargar el comentario
                </div>
            `;
        });
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
    button.innerHTML = '⏳ Procesando posts...';
    
    fetch('/api/fetch-new-posts', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.found_posts > 0) {
                // Show detailed processing results
                const failedCount = data.processed_posts - data.successful_posts;
                const processedText = data.processed_posts > 0 ? 
                    `✅ Exitosos: ${data.successful_posts} | ❌ Fallidos: ${failedCount} (${data.success_rate})` :
                    `✅ ${data.found_posts} posts encontrados (en cola)`;
                    
                button.innerHTML = processedText;
                
                // Log detailed results for debugging including errors
                console.log('Processing results:', {
                    found: data.found_posts,
                    processed: data.processed_posts,
                    successful: data.successful_posts,
                    failed: failedCount,
                    rate: data.success_rate,
                    results: data.results
                });
                
                // Log individual failures with details
                if (data.results) {
                    const failures = data.results.filter(r => !r.success);
                    if (failures.length > 0) {
                        console.group('❌ Processing Failures:');
                        failures.forEach(failure => {
                            console.error(`Post "${failure.title}": ${failure.error || 'Unknown error'}`);
                        });
                        console.groupEnd();
                    }
                }
                
                // Refresh the posts list after a short delay to show processed posts
                setTimeout(() => {
                    loadPosts();
                }, 3000);
            } else {
                button.innerHTML = '✅ No hay posts nuevos';
            }
        } else {
            button.innerHTML = '❌ Error al procesar';
            console.error('Error processing posts:', data.error);
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
                
                // Create error tooltip/title if there's an error message
                const errorInfo = post.error_message ? 
                    `title="Error: ${post.error_message.replace(/"/g, '&quot;')}"` : '';
                
                html += `
                    <tr>
                        <td>
                            <span class="post-title" 
                                  onclick="showCommentFromAPI('${post.post_id}', '${post.title.replace(/'/g, "\\'")}')">
                                ${truncatedTitle}
                            </span>
                        </td>
                        <td class="${statusClass}" ${errorInfo}>
                            ${statusText}
                            ${post.error_message ? '<br><small style="color: #666;">' + post.error_message.substring(0, 50) + (post.error_message.length > 50 ? '...' : '') + '</small>' : ''}
                        </td>
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
