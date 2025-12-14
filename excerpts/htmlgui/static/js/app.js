// ----------------------------------------
// 公共工具函数
// ----------------------------------------
function randomPastelColor() {
    // 柔和颜色：每个通道在 180-240 之间
    const r = Math.floor(Math.random() * 60 + 180);
    const g = Math.floor(Math.random() * 60 + 180);
    const b = Math.floor(Math.random() * 60 + 180);
    
    const toHex = (c) => c.toString(16).padStart(2, '0');
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}


// ----------------------------------------
// 标签动态渲染逻辑
// ----------------------------------------

const tagListContainer = document.getElementById('tagList');
const masonryContainer = document.getElementById('masonryContainer'); // 主内容区容器


function handleTagClick(event) {
    const clickedItem = event.currentTarget;
    const tagCid = clickedItem.dataset.cid; // 获取标签CID
    
    // 切换 active 状态
    const allItems = tagListContainer.querySelectorAll('.leftbar-item');
    allItems.forEach(item => {
        item.classList.remove('active');
    });
    clickedItem.classList.add('active');

    // 调用 API 获取该标签下的卡片
    renderCards(tagCid);
}

// 异步函数：从后端获取标签数据并渲染
async function fetchAndRenderTags() {
    try {
        // 假设 API 接口为 /api/tags
        const response = await fetch('/api/tags'); 
        if (!response.ok) throw new Error('Failed to fetch tags');
        const tagData = await response.json(); 
        
        tagListContainer.innerHTML = ''; 
        let defaultCid = 'all'; // 默认加载全部

        tagData.forEach(tag => {
            const item = document.createElement('div');
            item.className = 'leftbar-item';
            item.dataset.cid = tag.cid; 

            // 保持第一个标签为 active，并记下其 CID
            if (tag.isActive) {
                item.classList.add('active');
                defaultCid = tag.cid; 
            }
            item.title = `点击查看 ${tag.name} 标签下的摘录`;
            
            item.addEventListener('click', handleTagClick); 
            
            const nameSpan = document.createElement('span');
            nameSpan.style.setProperty('--tag-color', tag.color);
            nameSpan.textContent = tag.name;

            const countSpan = document.createElement('span');
            countSpan.textContent = `(${tag.count || 0})`; 

            item.appendChild(nameSpan);
            item.appendChild(countSpan);
            tagListContainer.appendChild(item);
        });

        // 默认加载第一个选中标签的卡片
        renderCards(defaultCid);
    } catch (error) {
        console.error('Error loading tags:', error);
        tagListContainer.innerHTML = '<div style="padding:10px; color:red;">加载标签失败</div>';
    }
}


// ----------------------------------------
// 卡片动态渲染逻辑
// ----------------------------------------

/**
 * 从后端获取卡片数据并渲染
 * @param {string} [tagCid='all'] - 标签CID，如果为'all'则获取全部
 */
async function renderCards(tagCid = 'all') {
    let url = `/api/excerpts/by_tag/${tagCid}`;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch cards');
        const cardData = await response.json(); 
        
        masonryContainer.innerHTML = ''; 
        
        cardData.forEach(data => {
            const card = document.createElement('div');
            card.className = 'card';
            card.style.background = randomPastelColor();
            card.dataset.cid = data.cid; 
            
            // 1. 日期
            const dateSpan = document.createElement('span');
            dateSpan.className = 'date';
            dateSpan.textContent = data.created_at || ''; 
            card.appendChild(dateSpan);
            
            // 2. 标题
            if (data.title && data.title !== '无') {
                const title = document.createElement('h3');
                title.className = 'card-title';
                title.textContent = data.title;
                card.appendChild(title);
            }

            // 3. 正文
            const content = document.createElement('p');
            content.className = 'card-text';
            content.textContent = data.content;
            card.appendChild(content);

            // 4. 作者 (右对齐)
            if (data.author && data.author !== '无') {
                const author = document.createElement('div');
                author.className = 'author';
                author.textContent = `—— ${data.author}`;
                card.appendChild(author);
            }
            
            // 5. 标签
            if (data.tags && data.tags.length > 0) {
                const tagsContainer = document.createElement('div');
                tagsContainer.className = 'card-tags';

                data.tags.filter(t => t.name !== '默认').forEach(tag => {
                    const tagSpan = document.createElement('span');
                    tagSpan.className = 'tag';
                    tagSpan.style.background = tag.color; 
                    tagSpan.textContent = tag.name;
                    tagsContainer.appendChild(tagSpan);
                });

                if (tagsContainer.children.length > 0) {
                    card.appendChild(tagsContainer);
                }
            }

            // 6 & 7. 底部内容：来源 + 按钮
            const footer = document.createElement('div');
            footer.className = 'card-footer';

            // 来源
            const sourceSpan = document.createElement('span');
            sourceSpan.className = 'source';
            sourceSpan.textContent = `摘自：${data.source || '未知'}`;
            
            // 按钮
            const actions = document.createElement('div');
            actions.className = 'actions';
            
            const editBtn = document.createElement('button');
            editBtn.className = 'btn small';
            editBtn.textContent = '编辑';
            editBtn.onclick = () => console.log(`编辑卡片: ${data.cid}`);
            
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn small danger';
            deleteBtn.textContent = '删除';
            deleteBtn.onclick = () => handleDeleteCard(data.cid); 

            actions.appendChild(editBtn);
            actions.appendChild(deleteBtn);
            
            footer.appendChild(sourceSpan); 
            footer.appendChild(actions); 
            
            card.appendChild(footer);

            masonryContainer.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading cards:', error);
        masonryContainer.innerHTML = '<p style="padding:20px; color:red;">加载摘录失败</p>';
    }
}

// 处理删除操作的函数
async function handleDeleteCard(cid) {
    if (!confirm('确认删除该摘录吗？')) return;

    try {
        const response = await fetch(`/api/excerpt/delete/${cid}`, {
            method: 'POST',
        });

        if (response.ok) {
            alert('删除成功！');
            // 重新加载当前视图的卡片
            const activeTag = document.querySelector('.leftbar-item.active');
            // 获取当前选中的标签 CID，然后重新渲染卡片列表
            renderCards(activeTag ? activeTag.dataset.cid : 'all'); 
        } else {
            throw new Error('Server returned an error.');
        }
    } catch (error) {
        console.error('Delete failed:', error);
        alert('删除失败，请检查服务器。');
    }
}


// ----------------------------------------
// 响应式菜单控制逻辑
// ----------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    // 菜单和左侧栏的响应式控制
    const menuBtn = document.querySelector('.menu-btn');
    const leftbar = document.querySelector('.leftbar');
    const closeBtn = document.querySelector('.close-btn');

    if (menuBtn && leftbar) {
        menuBtn.addEventListener('click', () => {
            leftbar.classList.toggle('is-open');
        });
    }

    if (closeBtn && leftbar) {
        closeBtn.addEventListener('click', () => {
            leftbar.classList.remove('is-open');
        });
    }
    
    // 页面加载完成后调用异步函数来获取并渲染标签
    fetchAndRenderTags(); 
});