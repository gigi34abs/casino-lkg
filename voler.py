import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class VolSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="voler", description="Tente un braquage à haut risque (Quitte ou Double)")
    @app_commands.describe(
        cible="Le joueur à détrousser",
        montant="Le montant que vous risquez pour ce vol (doit être dans votre poche)"
    )
    async def voler(self, interaction: discord.Interaction, cible: discord.Member, montant: int):
        # 1. Vérifications de base
        if montant <= 0:
            return await interaction.response.send_message("❌ Le montant doit être supérieur à 0.", ephemeral=True)
        
        if cible.id == interaction.user.id:
            return await interaction.response.send_message("❌ Tu ne peux pas te braquer toi-même, c'est ridicule.", ephemeral=True)

        cursor = self.bot.db.cursor()

        # 2. Vérifier l'argent du voleur
        cursor.execute("SELECT money FROM users WHERE user_id = ?", (interaction.user.id,))
        res_voleur = cursor.fetchone()
        argent_voleur = res_voleur[0] if res_voleur else 0

        if argent_voleur < montant:
            return await interaction.response.send_message(
                f"⚠️ **PRÉPARATION IMPOSSIBLE**\nTu n'as pas les **{montant} €** nécessaires en poche pour financer ce coup.", 
                ephemeral=True
            )

        # 3. Vérifier l'argent de la cible
        cursor.execute("SELECT money FROM users WHERE user_id = ?", (cible.id,))
        res_cible = cursor.fetchone()
        argent_cible = res_cible[0] if res_cible else 0

        if argent_cible < montant:
            return await interaction.response.send_message(
                f"🔍 **ÉCOUTAGE...**\n{cible.display_name} n'a pas autant de cash sur lui. Ça ne vaut pas le coup.", 
                ephemeral=True
            )

        # --- DÉBUT DE L'ACTION (SUSPENSE) ---
        embed_prep = discord.Embed(
            title="🥷 OPÉRATION EN COURS...",
            description=f"Tu tentes de dérober **{montant} €** à {cible.mention}.\n*Le plan est en cours d'exécution...*",
            color=0x2f3136
        )
        embed_prep.set_image(url="https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExNHJueXF3ZzR4ZzR4ZzR4ZzR4ZzR4ZzR4ZzR4ZzR4ZzR4JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/L3Y45TZEmKEn9UphP/giphy.gif") # Un petit GIF de code/hacking
        
        await interaction.response.send_message(embed=embed_prep)
        
        # On attend 2 secondes pour le suspense
        await asyncio.sleep(2)

        # 4. Logique du vol (50% de chance)
        reussite = random.choice([True, False])

        if reussite:
            # SUCCÈS
            cursor.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (montant, cible.id))
            cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (montant, interaction.user.id))
            self.bot.db.commit()

            embed_res = discord.Embed(
                title="✅ BRAQUAGE RÉUSSI !",
                description=(
                    f"🎯 **Cible neutralisée :** {cible.mention}\n"
                    f"💰 **Butin récupéré :** `{montant} €`\n\n"
                    "Tu as réussi à vider ses poches sans te faire prendre !"
                ),
                color=0x2ecc71 # Vert
            )
            embed_res.set_thumbnail(url="https://i.imgur.com/vHpxlYf.png") # Sac d'or
            embed_res.set_footer(text="Générateur de profit activé.")
        else:
            # ÉCHEC
            cursor.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (montant, interaction.user.id))
            self.bot.db.commit()

            embed_res = discord.Embed(
                title="🚨 ÉCHEC CRITIQUE !",
                description=(
                    f"👮 **La police est arrivée sur les lieux !**\n"
                    f"📉 **Perte sèche :** `-{montant} €` (Matériel saisi)\n\n"
                    f"{cible.mention} s'en sort indemne, mais tes fonds sont perdus."
                ),
                color=0xe74c3c # Rouge
            )
            embed_res.set_footer(text="Tu feras mieux la prochaine fois.")

        # Mise à jour du message avec le résultat final
        await interaction.edit_original_response(embed=embed_res)

async def setup(bot):
    await bot.add_cog(VolSystem(bot))
