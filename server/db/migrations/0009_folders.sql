-- SPDX-License-Identifier: GPL-3.0-or-later
-- cycle 169.76 — folder management schema (telegram desktop align)
-- 정합: app/ui/folder_edit_dialog.py + chat_list_panel.py ChatListEntry.folder_color

-- 사용자 정의 folder 영속화 — name + color + include/exclude chats
CREATE TABLE IF NOT EXISTS folders (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '폴더 PK',
    folder_id CHAR(8) NOT NULL UNIQUE COMMENT 'uuid hex 8자 — client folder_id 정합',
    owner_id INT UNSIGNED NOT NULL COMMENT 'users.id FK',
    name VARCHAR(64) NOT NULL COMMENT '폴더 표시명',
    color_name VARCHAR(16) COMMENT 'red/orange/purple/green/blue/indigo/pink',
    color_hex CHAR(7) COMMENT '#RRGGBB',
    chat_count INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '포함 대화 수 (denormalized cache)',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_folders_owner (owner_id),
    INDEX idx_folders_folder_id (folder_id),
    CONSTRAINT fk_folders_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '사용자 정의 chat 폴더';

-- 폴더 ↔ 대화방 N:M (include + exclude mode)
CREATE TABLE IF NOT EXISTS folder_chats (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    folder_id INT UNSIGNED NOT NULL COMMENT 'folders.id FK',
    chat_kind ENUM('friend', 'room', 'bot') NOT NULL COMMENT 'chat entry kind',
    chat_target_id INT UNSIGNED NOT NULL COMMENT 'kind 기반 friend/room/bot id',
    mode ENUM('include', 'exclude') NOT NULL DEFAULT 'include',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_folder_chats (folder_id, chat_kind, chat_target_id, mode),
    INDEX idx_folder_chats_folder (folder_id),
    CONSTRAINT fk_folder_chats_folder FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '폴더 ↔ 대화방 N:M include/exclude';

-- 폴더 공유 초대 링크
CREATE TABLE IF NOT EXISTS folder_invites (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    folder_id INT UNSIGNED NOT NULL COMMENT 'folders.id FK',
    invite_token CHAR(32) NOT NULL UNIQUE COMMENT 'secrets.token_hex(16) — 공유 URL 안 token',
    created_by INT UNSIGNED NOT NULL COMMENT 'users.id 생성자',
    expires_at TIMESTAMP COMMENT 'NULL = 영구 link',
    use_count INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '사용 횟수',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_folder_invites_folder (folder_id),
    INDEX idx_folder_invites_token (invite_token),
    CONSTRAINT fk_folder_invites_folder FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '폴더 공유 초대 link';
