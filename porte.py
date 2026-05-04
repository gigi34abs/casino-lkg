@group.command(name="portes", description="🚪 Tente de trouver le trésor derrière l'une des 3 portes")
    async def portes(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 1, 10000, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        # --- ACTION : On retire la mise DIRECTEMENT ---
        self.update_money(interaction.user.id, -pari)

        win_door = random.randint(1, 3)
        
        embed = discord.Embed(
            title="🚪 LE JEU DES PORTES", 
            description=(
                "Le trésor est caché derrière l'une de ces trois portes...\n"
                "**Fais le bon choix !** 🍀"
            ), 
            color=0x9B59B6
        )
        embed.add_field(name="💰 Mise engagée", value=f"**{self.fmt(pari)} €**", inline=True)
        embed.add_field(name="🏆 Jackpot", value=f"**{self.fmt(pari*3)} €** (x3)", inline=True)
        embed.set_footer(text="Une seule porte contient l'or, les autres sont vides.")

        class PortesView(discord.ui.View):
            def __init__(self, cog, win_door, pari, user):
                super().__init__(timeout=30)
                self.cog, self.win_door, self.pari, self.user = cog, win_door, pari, user

            async def play(self, i: discord.Interaction, choice: int):
                if i.user.id != self.user.id: 
                    return await i.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)

                # Construction du résultat visuel
                reveil = ""
                for n in range(1, 4):
                    if n == self.win_door:
                        reveil += f"Porte {n} : 💰 **TRÉSOR**"
                    else:
                        reveil += f"Porte {n} : 💨 **VIDE**"
                    
                    if choice == n:
                        reveil += " 👈 (Ton choix)"
                    reveil += "\n"

                res_embed = discord.Embed(description=reveil)

                if choice == self.win_door:
                    # VICTOIRE : On donne le x3 (Puisqu'on a déjà retiré le pari au début)
                    gain = self.pari * 3
                    self.cog.update_money(i.user.id, gain)
                    res_embed.title = "✨ INCROYABLE VICTOIRE !"
                    res_embed.color = 0xF1C40F
                    res_embed.add_field(name="Bilan", value=f"Tu as trouvé l'or ! Gain : **+{self.cog.fmt(gain)} €**")
                else:
                    # DÉFAITE : L'argent est déjà perdu (retiré au début)
                    res_embed.title = "💨 C'EST VIDE..."
                    res_embed.color = 0xE74C3C
                    res_embed.add_field(name="Bilan", value=f"Pas de chance ! Perte : **-{self.cog.fmt(self.pari)} €**")

                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="PORTE 1", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b1(self, i, b): await self.play(i, 1)
            @discord.ui.button(label="PORTE 2", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b2(self, i, b): await self.play(i, 2)
            @discord.ui.button(label="PORTE 3", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b3(self, i, b): await self.play(i, 3)

        await interaction.response.send_message(embed=embed, view=PortesView(self, win_door, pari, interaction.user))
