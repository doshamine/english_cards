create table word(id serial primary key not null, russian varchar(50) unique not null, english varchar(50) unique not null);
create table person(id serial primary key not null, chat_id bigint unique not null);
create table person_word(id serial primary key not null, id_person int not null references person(id), id_word int not null references word(id));

insert into word(russian, english)
     values ('зелёный', 'green'),
            ('красный', 'red'),
            ('жёлтый', 'yellow'),
            ('оранжевый', 'orange'),
            ('черный', 'black'),
            ('белый', 'white'),
            ('он', 'he'),
            ('она', 'she'),
            ('оно', 'it'),
            ('мы', 'we');


select * from word;