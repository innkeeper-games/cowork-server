create table room (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    public BOOLEAN NOT NULL,
    title VARCHAR(50) NOT NULL,
    owner_account_id VARCHAR(50) NOT NULL,
    persist_objects json
);

create table account (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    salt VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    wealth VARCHAR(50) NOT NULL,
    pfp VARCHAR(255)
);

create table membership (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    creation_date timestamp DEFAULT CURRENT_TIMESTAMP,
    account_id VARCHAR(50) NOT NULL,
    room_id VARCHAR(50) NOT NULL,
    FOREIGN KEY (account_id) REFERENCES account(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES room(id) ON DELETE CASCADE
);

create table invitation (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    creation_date timestamp DEFAULT CURRENT_TIMESTAMP,
    inviter_account_id VARCHAR(50) NOT NULL,
    invitee_account_id VARCHAR(50) NOT NULL,
    room_id VARCHAR(50) NOT NULL,
    FOREIGN KEY (inviter_account_id) REFERENCES account(id) ON DELETE CASCADE,
    FOREIGN KEY (inviter_account_id) REFERENCES account(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES room(id) ON DELETE CASCADE
);

create table chat (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    room_id VARCHAR(50) NOT NULL,
    sent_date timestamp DEFAULT NOW(),
    contents VARCHAR(255) NOT NULL,
    FOREIGN KEY (account_id) REFERENCES account(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES room(id) ON DELETE CASCADE
);

create table list (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    title VARCHAR(50) NOT NULL,
    room_id VARCHAR(50),
    inbox BOOLEAN NOT NULL,
    index SMALLINT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES account(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES room(id) ON DELETE CASCADE
);

create table task (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    public BOOLEAN NOT NULL,
    active BOOLEAN NOT NULL,
    title VARCHAR NOT NULL,
    contents VARCHAR NOT NULL,
    room_id VARCHAR(50),
    FOREIGN KEY (account_id) REFERENCES account(id) ON DELETE CASCADE,
    FOREIGN KEY (list_id) REFERENCES list(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES room(id) ON DELETE CASCADE
);

create table assignment (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    task_id VARCHAR(50) NOT NULL,
    FOREIGN KEY (account_id) REFERENCES account(id) ON DELETE CASCADE
);


create table listing (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    task_id VARCHAR(50) NOT NULL,
    list_id VARCHAR(50) NOT NULL,
    index SMALLINT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (account_id) REFERENCES account(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES task(id) ON DELETE CASCADE,
    FOREIGN KEY (list_id) REFERENCES list(id) ON DELETE CASCADE
);

create table tag (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    color SMALLINT NOT NULL,
    title VARCHAR NOT NULL,
);

create table tagging (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    tag_id VARCHAR(50) NOT NULL,
    listing_id VARCHAR(50) NOT NULL,
    FOREIGN KEY (tag_id) REFERENCES tag(id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES listing(id) ON DELETE CASCADE
);