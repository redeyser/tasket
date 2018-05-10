Идея этого поделия следующая. Создаем текстовый файл с разметкой, предполагающей разбиение на записи и теги внутри записей. Далее, с помощью данной проги осуществляем управление этим файлом. То есть добавление записей, тегов, хеширование, индексирование, выборка, мердж.

К этому поделию можно сделать любой фронт. Веб, консоль (попытка ncurs_tasket) и просто автоматизированный пакетный режим.

Условия: (равно, неравно,содержит, несодержит)
ZN = ['=','^','~','/']

Выборка всей записи :
./tasket.py -f mem.txt -n 04ec92eecf8311e796eae0cb4e458e4f

Выборка тегов записи :
./tasket.py -f mem.txt -n 04ec92eecf8311e796eae0cb4e458e4f -k TEXT

Выборка списком с условием:
./tasket.py -f mem.txt -l line -k ID:HEAD -i ID~merch

Выборка частей записей tag/content с условием:
./tasket.py -f mem.txt -l part -k ID:HEAD -i ID~merch

Выбока по номеру или uuid записи:
./tasket.py -f mem.txt -n 2 > data.txt
./tasket.py -f mem.txt -k ID:HEAD -n 2
./tasket.py -f mem.txt -k ID:HEAD -n 04ec92e1cf8311e796eae0cb4e458e4f

Вывод содержимого тега:
./tasket.py -f mem.txt -n 04ec92eecf8311e796eae0cb4e458e4f -o True -k TEXT

Добавить новую запись (генерируется UUID):
./tasket.py -f mem.txt -u add -r data.txt
Выводит сгенерированный uuid 04ec92e2cf8311e796eae0cb4e458e4f

Жесткая перезапись (default merge = False). Изменить запись по ID: 
./tasket.py -f mem.txt -u id -n 04ec92e2cf8311e796eae0cb4e458e4f -r data.txt
заменит всю запись. Если в новом контенте нет uuid, то назначит НОВЫЙ. Считается что запись новая!

Мягкая перезапись (merge = True). Изменить с наложением пересекающегося контента.
./tasket.py -f mem.txt -u id -n 04ec92e2cf8311e796eae0cb4e458e4f -m True -r data.txt
В данном случае отсортирует теги, добавит, если не было UUID. Перезапишет частично

Конвеерная перезапись (default merge = False). UUID берется из самого тела
./tasket.py -f mem.txt -u cont -r data.txt

Конвеерная мягкая перезапись (merge = True). UUID берется из самого тела
./tasket.py -f mem.txt -u cont -m True -r data.txt

Запись содержимомго тега или добавление тега:
echo "new content" | ./tasket.py -f mem.txt -n 04ec92eecf8311e796eae0cb4e458e4f -u id -m True -o True -k NEWTAG -r -
./tasket.py -f mem.txt -n 04ec92eecf8311e796eae0cb4e458e4f -u id -m True -o True -k NEWTAG -r new_content

Массовая мягкая перезапись.
./tasket.py -f mem.txt -l part -k ID:HEAD:UUID:TYPE -i ID~merch >head.txt
./tasket.py -f mem.txt -u part -m True -r head.txt

Удаление записи:
./tasket.py -f mem.txt -u delete -n 3 
./tasket.py -f mem.txt -u delete -n 04ec92eecf8311e796eae0cb4e458e4f 

Переупаковка:
./tasket.py -f mem.txt --repack True

Выборка сервисной инфы
./tasket.py -f mem.txt -l index

Выборка сервисной инфы
 ( R_ORDER     = ["R_UUID","R_HASH","R_TM","R_START","R_RSIZE","R_MSIZE","R_STATUS"] )
./tasket.py -f mem.txt -i R_ID=4 -l index
./tasket.py -f mem.txt -i R_UUID=04ec9312cf8311e796eae0cb4e458e4f -l index
./tasket.py -f mem.txt -l index -i R_STATUS^full;R_HASH=910c95be84900ac3d03385f769f1169d
