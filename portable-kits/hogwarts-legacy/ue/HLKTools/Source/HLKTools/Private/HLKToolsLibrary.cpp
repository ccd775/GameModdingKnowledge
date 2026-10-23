#include "HLKToolsLibrary.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimInstance.h"
#include "Animation/Skeleton.h"
#include "AnimationGraphSchema.h"
#include "BoneControllers/AnimNode_AnimDynamics.h"
#include "AnimGraphNode_ComponentToLocalSpace.h"
#include "AnimGraphNode_CopyPoseFromMesh.h"
#include "AnimGraphNode_LinkedInputPose.h"
#include "AnimGraphNode_LocalToComponentSpace.h"
#include "AnimGraphNode_Root.h"
#include "AssetRegistryModule.h"
#include "Dom/JsonObject.h"
#include "EdGraph/EdGraph.h"
#include "EdGraphSchema_K2.h"
#include "Factories/AnimBlueprintFactory.h"
#include "JsonObjectConverter.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

DEFINE_LOG_CATEGORY_STATIC(LogHLK, Log, All);

namespace
{
	template <typename T>
	T* NewNode(UEdGraph* Graph, int32 X, int32 Y, TFunctionRef<void(T*)> Setup)
	{
		FGraphNodeCreator<T> Creator(*Graph);
		T* Node = Creator.CreateNode();
		Node->NodePosX = X;
		Node->NodePosY = Y;
		Setup(Node);  // before pins are allocated, so exposed pins take these values as defaults
		Creator.Finalize();
		return Node;
	}

	UEdGraphPin* PosePin(UEdGraphNode* Node, EEdGraphPinDirection Dir)
	{
		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (Pin->Direction == Dir && (UAnimationGraphSchema::IsPosePin(Pin->PinType) || UAnimationGraphSchema::IsComponentSpacePosePin(Pin->PinType)))
			{
				return Pin;
			}
		}
		return nullptr;
	}

	// same as FGraphNodeCreator, for node classes that aren't DLL-exported (UAnimGraphNode_AnimDynamics)
	UEdGraphNode* NewNodeOfClass(UEdGraph* Graph, UClass* Class, int32 X, int32 Y, TFunctionRef<void(UEdGraphNode*)> Setup)
	{
		UEdGraphNode* Node = NewObject<UEdGraphNode>(Graph, Class);
		Node->SetFlags(RF_Transactional);
		Graph->AddNode(Node, false, false);
		Node->NodePosX = X;
		Node->NodePosY = Y;
		Setup(Node);
		Node->CreateNewGuid();
		Node->PostPlacedNewNode();
		if (Node->Pins.Num() == 0)
		{
			Node->AllocateDefaultPins();
		}
		return Node;
	}

	// the runtime node struct ("Node") is private on some graph nodes (AnimDynamics); reach it through reflection
	template <typename TStruct>
	TStruct* RuntimeNode(UEdGraphNode* GraphNode)
	{
		FStructProperty* Prop = FindFProperty<FStructProperty>(GraphNode->GetClass(), TEXT("Node"));
		check(Prop && Prop->Struct == TStruct::StaticStruct());
		return Prop->ContainerPtrToValuePtr<TStruct>(GraphNode);
	}

	bool FillFromJson(UEdGraphNode* GraphNode, const TSharedRef<FJsonObject>& Json)
	{
		FStructProperty* Prop = FindFProperty<FStructProperty>(GraphNode->GetClass(), TEXT("Node"));
		return Prop && FJsonObjectConverter::JsonObjectToUStruct(Json, Prop->Struct, Prop->ContainerPtrToValuePtr<void>(GraphNode), 0, 0);
	}

	bool Link(UEdGraph* Graph, UEdGraphNode* From, UEdGraphNode* To)
	{
		UEdGraphPin* Out = PosePin(From, EGPD_Output);
		UEdGraphPin* In = PosePin(To, EGPD_Input);
		if (!Out || !In)
		{
			UE_LOG(LogHLK, Error, TEXT("missing pose pin %s -> %s"), *From->GetName(), *To->GetName());
			return false;
		}
		if (!Graph->GetSchema()->TryCreateConnection(Out, In))
		{
			UE_LOG(LogHLK, Error, TEXT("cannot link %s -> %s"), *From->GetName(), *To->GetName());
			return false;
		}
		return true;
	}
}

UAnimBlueprint* UHLKToolsLibrary::CreateDynamicsAnimBlueprint(const FString& PackagePath, USkeleton* Skeleton, const FString& CopyPoseJson, const FString& DynamicsJson)
{
	if (!Skeleton)
	{
		UE_LOG(LogHLK, Error, TEXT("no skeleton"));
		return nullptr;
	}
	TArray<TSharedPtr<FJsonValue>> Chains;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(DynamicsJson), Chains))
	{
		UE_LOG(LogHLK, Error, TEXT("DynamicsJson is not a JSON array"));
		return nullptr;
	}
	TSharedPtr<FJsonObject> CopyPose;
	if (!CopyPoseJson.IsEmpty() && !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(CopyPoseJson), CopyPose))
	{
		UE_LOG(LogHLK, Error, TEXT("CopyPoseJson is not a JSON object"));
		return nullptr;
	}

	const FString AssetName = FPackageName::GetLongPackageAssetName(PackagePath);
	UPackage* Package = CreatePackage(*PackagePath);
	UAnimBlueprintFactory* Factory = NewObject<UAnimBlueprintFactory>();
	Factory->TargetSkeleton = Skeleton;
	Factory->ParentClass = UAnimInstance::StaticClass();
	Factory->BlueprintType = BPTYPE_Normal;
	UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(Factory->FactoryCreateNew(UAnimBlueprint::StaticClass(), Package, FName(*AssetName), RF_Public | RF_Standalone | RF_Transactional, nullptr, GWarn));
	if (!AnimBP)
	{
		UE_LOG(LogHLK, Error, TEXT("factory failed for %s"), *PackagePath);
		return nullptr;
	}
	FAssetRegistryModule::AssetCreated(AnimBP);

	UEdGraph* Graph = nullptr;
	for (UEdGraph* G : AnimBP->FunctionGraphs)
	{
		if (G->GetFName() == UEdGraphSchema_K2::GN_AnimGraph)
		{
			Graph = G;
		}
	}
	TArray<UAnimGraphNode_Root*> Roots;
	if (Graph)
	{
		Graph->GetNodesOfClass<UAnimGraphNode_Root>(Roots);
	}
	if (!Graph || Roots.Num() != 1)
	{
		UE_LOG(LogHLK, Error, TEXT("no AnimGraph/root in %s"), *PackagePath);
		return nullptr;
	}

	UClass* DynClass = FindObject<UClass>(ANY_PACKAGE, TEXT("AnimGraphNode_AnimDynamics"));
	if (!DynClass)
	{
		UE_LOG(LogHLK, Error, TEXT("AnimGraphNode_AnimDynamics class not found"));
		return nullptr;
	}
	int32 X = -400 * (Chains.Num() + 4);
	UEdGraphNode* Prev = nullptr;
	if (CopyPose.IsValid())
	{
		Prev = NewNode<UAnimGraphNode_CopyPoseFromMesh>(Graph, X, 0, [&](UAnimGraphNode_CopyPoseFromMesh* N) {
			FillFromJson(N, CopyPose.ToSharedRef());
		});
	}
	else
	{
		Prev = NewNode<UAnimGraphNode_LinkedInputPose>(Graph, X, 0, [](UAnimGraphNode_LinkedInputPose*) {});
	}
	X += 400;
	UEdGraphNode* ToComponent = NewNode<UAnimGraphNode_LocalToComponentSpace>(Graph, X, 0, [](UAnimGraphNode_LocalToComponentSpace*) {});
	bool bOk = Link(Graph, Prev, ToComponent);
	Prev = ToComponent;
	for (const TSharedPtr<FJsonValue>& Value : Chains)
	{
		X += 400;
		const TSharedPtr<FJsonObject>* Obj = nullptr;
		if (!Value->TryGetObject(Obj))
		{
			UE_LOG(LogHLK, Error, TEXT("dynamics entry is not an object"));
			return nullptr;
		}
		UEdGraphNode* Dyn = NewNodeOfClass(Graph, DynClass, X, 0, [&](UEdGraphNode* N) {
			if (!FillFromJson(N, Obj->ToSharedRef()))
			{
				UE_LOG(LogHLK, Error, TEXT("bad AnimDynamics json"));
			}
		});
		const FAnimNode_AnimDynamics* DynNode = RuntimeNode<FAnimNode_AnimDynamics>(Dyn);
		UE_LOG(LogHLK, Display, TEXT("AnimDynamics %s -> %s chain=%d"), *DynNode->BoundBone.BoneName.ToString(), *DynNode->ChainEnd.BoneName.ToString(), (int32)DynNode->bChain);
		bOk &= Link(Graph, Prev, Dyn);
		Prev = Dyn;
	}
	X += 400;
	UEdGraphNode* ToLocal = NewNode<UAnimGraphNode_ComponentToLocalSpace>(Graph, X, 0, [](UAnimGraphNode_ComponentToLocalSpace*) {});
	bOk &= Link(Graph, Prev, ToLocal);
	bOk &= Link(Graph, ToLocal, Roots[0]);
	if (!bOk)
	{
		return nullptr;
	}

	FCompilerResultsLog Results;
	FKismetEditorUtilities::CompileBlueprint(AnimBP, EBlueprintCompileOptions::None, &Results);
	for (const TSharedRef<FTokenizedMessage>& Message : Results.Messages)
	{
		UE_LOG(LogHLK, Display, TEXT("compile: %s"), *Message->ToText().ToString());
	}
	if (AnimBP->Status == BS_Error)
	{
		UE_LOG(LogHLK, Error, TEXT("compile failed for %s"), *PackagePath);
		return nullptr;
	}
	Package->MarkPackageDirty();
	UE_LOG(LogHLK, Display, TEXT("created %s with %d dynamics nodes"), *PackagePath, Chains.Num());
	return AnimBP;
}
