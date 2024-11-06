import aiosqlite
import asyncio

async def remove_duplicates():
    conn = await aiosqlite.connect("ads.db", timeout=10)
    c = await conn.cursor()

    # Находим дублирующиеся ссылки
    await c.execute("""
        SELECT link, MIN(rowid) as min_rowid
        FROM olx
        GROUP BY link
        HAVING COUNT(link) > 1
    """)
    duplicates = await c.fetchall()

    # Удаляем все дубликаты, оставляя только одну запись
    for link, min_rowid in duplicates:
        await c.execute("DELETE FROM olx WHERE link = ? AND rowid != ?", (link, min_rowid))

    await conn.commit()
    await conn.close()
    print("Все дубликаты удалены.")

if __name__ == "__main__":
    asyncio.run(remove_duplicates())