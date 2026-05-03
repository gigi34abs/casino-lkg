import discord
from discord import app_commands
from discord.ext import commands, tasks
import time

class Boutique(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configuration des IDs
        self.ID_ROLE_VIP = 1499809955841310871
        self.ID_CATEGORIE_CASINO = 1498394439079559318

        # --- TES PRIX ET REVENUS ---
        self.entreprises = {
            "Boulangerie": {"prix": 150000, "revenu": 650},
            "Casino Local": {"prix": 250000, "revenu": 1000},
            "Banque Privée": {"prix": 500000, "revenu": 1750},
            "Empire Pétrolier": {"prix": 1500000, "revenu": 2500}
        }
        self.recolte_auto.start()

    def cog_unload(self):
        self.recolte_auto.cancel()

    # --- LA BARRIÈRE DE SÉCURITÉ (Bloque VIP + Catégorie) ---
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user_role_ids = [role.id for role in interaction.user.roles]
        if self.ID_ROLE_VIP not in user_role_ids:
            await interaction.response.send_message("🚫 **Accès refusé** : Le rôle VIP est requis pour accéder à la boutique.", ephemeral=True)
            return False

        current_cat = getattr(interaction.channel, 'category_id', None)
        if current_cat != self.ID_CATEGORIE_CASINO:
            await interaction.response.send_message(f"🎰 **Mauvais salon** : La boutique n'est accessible que dans la catégorie <#{self.ID_CATEGORIE_CASINO}>.", ephemeral=True)
            return False

        return True

    def get_user_biens(self, user_id):
        """Récupère l'argent et les entreprises d'un joueur"""
        cursor = self.bot.db.cursor()
        # On s'assure que l'utilisateur existe
        cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        self.bot.db.commit()
        
        cursor.execute("SELECT money, banque, entreprises FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        import json
        try:
            ents = json.loads(row[2]) if row[2] else {}
        except:
            ents = {}
            
        return {
            "portefeuille": row[0],
            "banque": row[1],
            "entreprises": ents
        }

    def save_user_biens(self, user_id, u):
        """Sauvegarde l'argent et les entreprises dans SQLite"""
        import json
        ents_json = json.dumps(u["entreprises"])
        cursor = self.bot.db.cursor()
        cursor.execute('''
            UPDATE users SET money = ?, banque = ?, entreprises = ? 
            WHERE user_id = ?
        ''', (u["portefeuille"], u["banque"], ents_json, user_id))
        self.bot.db.commit()

    # --- RÉCOLTE AUTOMATIQUE ---
    @tasks.loop(minutes=30)
    async def recolte_auto(self):
        import json
        cursor = self.bot.db.cursor()
        cursor.execute("SELECT user_id, banque, entreprises FROM users")
        rows = cursor.fetchall()
        
        for row in rows:
            uid, banque, ents_str = row
            if ents_str:
                try:
                    ents = json.loads(ents_str)
                    total_revenu = 0
                    for nom, qte in ents.items():
                        if nom in self.entreprises:
                            total_revenu += self.entreprises[nom]["revenu"] * qte
                    
                    if total_revenu > 0:
                        nouveau_solde = banque + total_revenu
                        cursor.execute("UPDATE users SET banque = ? WHERE user_id = ?", (nouveau_solde, uid))
                except:
                    continue
        self.bot.db.commit()

    group = app_commands.Group(name="boutique", description="🏭 Investissements de luxe")

    # --- LISTE DES PRIX ---
    @group.command(name="liste", description="Voir le catalogue immobilier")
    async def liste(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🏢 MARCHÉ DES GRANDS INVESTISSEURS", color=0x2c3e50)
        embed.set_footer(text="Revenus versés automatiquement en banque toutes les 30 min.")
        
        for nom, info in self.entreprises.items():
            prix_f = f"{info['prix']:,} €".replace(',', ' ')
            rev_f = f"{info['revenu']:,} €".replace(',', ' ')
            embed.add_field(
                name=f"🔹 {nom}", 
                value=f"Prix d'achat : **{prix_f}**\nGain passif : **+{rev_f}**", 
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    # --- ACHETER ---
    @group.command(name="acheter", description="Devenir propriétaire")
    async def acheter(self, interaction: discord.Interaction, entreprise: str):
        ent_nom = None
        for key in self.entreprises.keys():
            if key.lower() == entreprise.lower():
                ent_nom = key
                break

        if not ent_nom:
            return await interaction.response.send_message("❌ Entreprise introuvable dans le catalogue.", ephemeral=True)

        u = self.get_user_biens(interaction.user.id)
        info = self.entreprises[ent_nom]

        if u["portefeuille"] < info["prix"]:
            manquant = info["prix"] - u["portefeuille"]
            return await interaction.response.send_message(f"❌ Il te manque **{manquant:,} €** en liquide !".replace(',', ' '), ephemeral=True)

        u["portefeuille"] -= info["prix"]
        u["entreprises"][ent_nom] = u["entreprises"].get(ent_nom, 0) + 1
        
        self.save_user_biens(interaction.user.id, u)
        await interaction.response.send_message(f"🏦 **Félicitations !** Tu viens d'acquérir : **{ent_nom}** !")

    # --- MES BIENS ---
    @group.command(name="mes_biens", description="Voir tes titres de propriété")
    async def mes_biens(self, interaction: discord.Interaction):
        u = self.get_user_biens(interaction.user.id)
        
        embed = discord.Embed(title=f"📁 PATRIMOINE DE {interaction.user.display_name}", color=0xf39c12)
        
        if not u.get("entreprises"):
            embed.description = "Tu ne possèdes aucun actif pour le moment."
        else:
            total_rev = 0
            txt = ""
            for nom, qte in u["entreprises"].items():
                if nom in self.entreprises:
                    rev = self.entreprises[nom]["revenu"] * qte
                    total_rev += rev
                    txt += f"🏢 **{nom}** x{qte} | `+{rev:,} €` /30min\n"
            
            embed.description = txt.replace(',', ' ')
            embed.add_field(name="💰 Revenu Passif Total", value=f"**`{total_rev:,} €`** toutes les 30 minutes".replace(',', ' '))
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Boutique(bot))
